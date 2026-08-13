using System.Text.Json.Serialization;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Rooms;
using MegaCrit.Sts2.Core.AutoSlay.Helpers;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.Events;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Ai;

[HarmonyPatch(typeof(EventRoomHandler), nameof(EventRoomHandler.HandleAsync))]
internal static class EventRoomHandlerPatch
{
    private static bool _bypass;

    private static bool Prefix(Rng random, CancellationToken ct, ref Task __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent") || _bypass)
            return true;
        __result = PreferByrdonisEgg(random, ct);
        return false;
    }

    private static async Task PreferByrdonisEgg(Rng random, CancellationToken ct)
    {
        var root = ((SceneTree)Engine.GetMainLoop()).Root;
        var room = await WaitHelper.ForNode<Node>(root, "/root/Game/RootSceneContainer/Run/RoomContainer/EventRoom", ct);
        var egg = UiHelper.FindAll<NEventOptionButton>(room).FirstOrDefault(button =>
            button.Event.Id.Entry == "BYRDONIS_NEST" && button.Option.TextKey.EndsWith("TAKE") && !button.Option.IsLocked);
        if (egg is not null)
        {
            AgentIo.Trace(new { phase = "event", event_id = egg.Event.Id.Entry, option = "TAKE_BYRDONIS_EGG" });
            await UiHelper.Click(egg);
        }
        var tablet = UiHelper.FindAll<NEventOptionButton>(room).FirstOrDefault(button =>
            button.Event.Id.Entry == "TABLET_OF_TRUTH" && button.Option.TextKey.EndsWith(".SMASH") && !button.Option.IsLocked);
        if (tablet is not null)
        {
            AgentIo.Trace(new { phase = "event", event_id = tablet.Event.Id.Entry, option = "SMASH" });
            await UiHelper.Click(tablet);
        }
        await DelegateRelicChoices(room, ct);
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

    private sealed record EventAction(
        int Seq,
        string Type,
        [property: JsonPropertyName("option_index")] int? OptionIndex,
        [property: JsonPropertyName("relic_id")] string? RelicId) : IAgentAction;

    /// <summary>
    /// Ancient events (e.g. PAEL at Act 2 start) offer several relics; the default handler
    /// picks one at random, which can add unplayable cards to the deck (PaelsHorn adds 2 Relax).
    /// Delegate the relic choice to the agent so the best option is picked instead.
    /// </summary>
    private static async Task DelegateRelicChoices(Node room, CancellationToken ct)
    {
        var ancient = UiHelper.FindFirst<NAncientEventLayout>(room);
        if (ancient is null)
            return;
        await ClickThroughAncientDialogue(ancient, ct);
        var options = UiHelper.FindAll<NEventOptionButton>(ancient)
            .Where(button => button.IsEnabled && !button.Option.IsLocked && button.Option.Relic is not null)
            .ToList();
        if (options.Count < 2)
            return;

        var run = RunManager.Instance.DebugOnlyGetState();
        var player = LocalContext.GetMe(run);
        int seq = AgentIo.NextSequence();
        AgentIo.WriteObservation(new
        {
            seq,
            terminal = false,
            phase = "event",
            run = new { act = run?.CurrentActIndex, floor = run?.ActFloor },
            player = new
            {
                hp = player?.Creature.CurrentHp,
                max_hp = player?.Creature.MaxHp,
                gold = player?.Gold,
                deck = player?.Deck.Cards.Select(card => card.Id.ToString()),
                relics = player?.Relics.Select(relic => relic.Id.ToString()),
            },
            event_id = options[0].Event.Id.Entry,
            options = options.Select((button, index) => new
            {
                index,
                relic_id = button.Option.Relic!.Id.ToString(),
                title = button.Option.Title.GetFormattedText(),
            }),
            legal_actions = options.Select((button, index) => new
            {
                type = "event_relic",
                option_index = index,
                relic_id = button.Option.Relic!.Id.ToString(),
            }),
        });
        var action = await AgentIo.AwaitAction<EventAction>(seq, ct);
        if (action.Type == "event_relic" && action.OptionIndex is int optionIndex &&
            optionIndex >= 0 && optionIndex < options.Count &&
            action.RelicId == options[optionIndex].Option.Relic!.Id.ToString())
        {
            AgentIo.Trace(new { seq, phase = "event", event_id = options[0].Event.Id.Entry, option_index = optionIndex, relic_id = action.RelicId });
            await UiHelper.Click(options[optionIndex]);
        }
        else
        {
            AgentIo.Trace(new { seq, phase = "event", event_id = options[0].Event.Id.Entry, action = "skip", reason = "invalid_relic_action" });
        }
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
        await WaitHelper.Until(() => UiHelper.FindAll<NEventOptionButton>(ancientLayout).Any(button => button.IsEnabled && !button.Option.IsLocked), ct, TimeSpan.FromSeconds(10L), "Ancient event options did not become available after dialogue");
    }
}
