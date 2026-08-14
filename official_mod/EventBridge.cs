using System.Text.Json.Serialization;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Rooms;
using MegaCrit.Sts2.Core.AutoSlay.Helpers;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Events;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;
using MegaCrit.Sts2.Core.Nodes.Screens.Overlays;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Ai;

[HarmonyPatch(typeof(EventRoomHandler), nameof(EventRoomHandler.HandleAsync))]
internal static class EventRoomHandlerPatch
{
    private static bool _bypass;

    private enum EventChoiceResult
    {
        Fallback,
        Chosen,
        Completed,
    }

    private sealed record EventAction(
        int Seq,
        string Type,
        [property: JsonPropertyName("option_index")] int? OptionIndex,
        [property: JsonPropertyName("text_key")] string? TextKey,
        [property: JsonPropertyName("relic_id")] string? RelicId) : IAgentAction;

    private static bool Prefix(Rng random, CancellationToken ct, ref Task __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent") || _bypass)
            return true;
        __result = Handle(random, ct);
        return false;
    }

    private static async Task Handle(Rng random, CancellationToken ct)
    {
        var root = ((SceneTree)Engine.GetMainLoop()).Root;
        var room = await WaitHelper.ForNode<Node>(root, "/root/Game/RootSceneContainer/Run/RoomContainer/EventRoom", ct);
        for (int iteration = 0; iteration < 50; iteration++)
        {
            EventChoiceResult result = await DelegateEventChoice(room, ct);
            if (result == EventChoiceResult.Completed)
                return;
            if (result == EventChoiceResult.Fallback)
                break;
            if (!GodotObject.IsInstanceValid(room) || !room.IsInsideTree())
                return;
            await Task.Delay(100, ct);
        }

        _bypass = true;
        try
        {
            await new EventRoomHandler().HandleAsync(random, ct);
        }
        finally
        {
            _bypass = false;
        }
    }

    private static async Task<EventChoiceResult> DelegateEventChoice(Node room, CancellationToken ct)
    {
        var ancient = UiHelper.FindFirst<NAncientEventLayout>(room);
        if (ancient is not null)
            await ClickThroughAncientDialogue(ancient, ct);

        var indexed = UiHelper.FindAll<NEventOptionButton>(room)
            .Select((button, index) => new { Button = button, Index = index })
            .ToArray();
        if (indexed.Length == 0)
            return EventChoiceResult.Fallback;
        var eligible = indexed.Where(item => item.Button.IsEnabled && IsSafe(item.Button)).ToArray();
        if (eligible.Length == 0)
            return EventChoiceResult.Fallback;

        var run = RunManager.Instance.DebugOnlyGetState();
        var player = run is null ? null : LocalContext.GetMe(run);
        if (run is null || player is null)
            return EventChoiceResult.Fallback;
        int seq = AgentIo.NextSequence();
        string eventId = indexed[0].Button.Event.Id.Entry;
        AgentIo.WriteObservation(new
        {
            seq,
            terminal = false,
            phase = "event",
            run = new { act = run.CurrentActIndex, floor = run.ActFloor },
            player = new
            {
                hp = player.Creature.CurrentHp,
                max_hp = player.Creature.MaxHp,
                gold = player.Gold,
                deck = player.Deck.Cards.Select(card => card.Id.ToString()),
                relics = player.Relics.Select(relic => relic.Id.ToString()),
            },
            event_id = eventId,
            options = indexed.Select(item => new
            {
                option_index = item.Index,
                text_key = item.Button.Option.TextKey,
                is_proceed = item.Button.Option.IsProceed,
                is_locked = item.Button.Option.IsLocked,
                relic_id = item.Button.Option.Relic?.Id.ToString(),
                title = item.Button.Option.Title.GetFormattedText(),
            }),
            legal_actions = eligible.Select(item => new
            {
                type = "event_option",
                option_index = item.Index,
                text_key = item.Button.Option.TextKey,
                is_proceed = item.Button.Option.IsProceed,
                relic_id = item.Button.Option.Relic?.Id.ToString(),
            }),
        });

        EventAction action;
        try
        {
            action = await AgentIo.AwaitAction<EventAction>(seq, ct);
        }
        catch (TimeoutException)
        {
            AgentIo.Trace(new { seq, phase = "event", event_id = eventId, action = "fallback", reason = "agent_timeout" });
            return EventChoiceResult.Fallback;
        }

        if (action.Type != "event_option" || action.OptionIndex is not int optionIndex ||
            optionIndex < 0 || optionIndex >= indexed.Length)
        {
            AgentIo.Trace(new { seq, phase = "event", event_id = eventId, action = "fallback", reason = "invalid_event_action" });
            return EventChoiceResult.Fallback;
        }
        var selected = indexed[optionIndex].Button;
        if (!eligible.Any(item => item.Index == optionIndex) || selected.Option.TextKey != action.TextKey ||
            selected.Option.Relic?.Id.ToString() != action.RelicId)
        {
            AgentIo.Trace(new { seq, phase = "event", event_id = eventId, action = "fallback", reason = "invalid_event_action" });
            return EventChoiceResult.Fallback;
        }

        AgentIo.Trace(new
        {
            seq,
            phase = "event",
            event_id = eventId,
            option_index = optionIndex,
            text_key = selected.Option.TextKey,
            relic_id = selected.Option.Relic?.Id.ToString(),
        });
        var previous = indexed.Where(item => !item.Button.Option.IsLocked).Select(item => item.Button).ToHashSet();
        await UiHelper.Click(selected);

        try
        {
            if (selected.Option.IsProceed)
            {
                await WaitHelper.Until(
                    () => !GodotObject.IsInstanceValid(room) || !room.IsInsideTree() || NMapScreen.Instance?.IsOpen == true,
                    ct,
                    TimeSpan.FromSeconds(5),
                    "Event room did not close after clicking proceed");
                return EventChoiceResult.Completed;
            }
            await WaitHelper.Until(
                () =>
                    !GodotObject.IsInstanceValid(room) || !room.IsInsideTree() ||
                    NMapScreen.Instance?.IsOpen == true ||
                    NOverlayStack.Instance?.ScreenCount > 0 ||
                    CombatManager.Instance.IsInProgress ||
                    !previous.SetEquals(UiHelper.FindAll<NEventOptionButton>(room).Where(button => !button.Option.IsLocked)),
                ct,
                TimeSpan.FromSeconds(5),
                "Event options did not change after choice");
        }
        catch (TimeoutException)
        {
            AgentIo.Trace(new { seq, phase = "event", event_id = eventId, action = "fallback", reason = "event_did_not_advance" });
            return EventChoiceResult.Fallback;
        }

        if (!GodotObject.IsInstanceValid(room) || !room.IsInsideTree() || NMapScreen.Instance?.IsOpen == true)
            return EventChoiceResult.Completed;
        if (NOverlayStack.Instance?.ScreenCount > 0 || CombatManager.Instance.IsInProgress)
            return EventChoiceResult.Fallback;
        return EventChoiceResult.Chosen;
    }

    private static bool IsSafe(NEventOptionButton button)
    {
        var killer = button.Option.WillKillPlayer;
        var owner = button.Event.Owner;
        return !button.Option.IsLocked && (killer is null || owner is null || !killer(owner));
    }

    private static async Task ClickThroughAncientDialogue(NAncientEventLayout ancientLayout, CancellationToken ct)
    {
        int clicks = 0;
        while (clicks < 50)
        {
            ct.ThrowIfCancellationRequested();
            if (!GodotObject.IsInstanceValid(ancientLayout))
                break;
            if (UiHelper.FindAll<NEventOptionButton>(ancientLayout).Any(button => button.IsEnabled && !button.Option.IsLocked))
                break;
            var hitbox = ancientLayout.GetNodeOrNull<NButton>("%DialogueHitbox");
            if (hitbox is null || !hitbox.Visible || !hitbox.IsEnabled)
            {
                await Task.Delay(100, ct);
                continue;
            }
            hitbox.EmitSignal(NClickableControl.SignalName.Released, hitbox);
            clicks++;
            await Task.Delay(500, ct);
        }
        await WaitHelper.Until(
            () => UiHelper.FindAll<NEventOptionButton>(ancientLayout).Any(button => button.IsEnabled && !button.Option.IsLocked),
            ct,
            TimeSpan.FromSeconds(10),
            "Ancient event options did not become available after dialogue");
    }
}
