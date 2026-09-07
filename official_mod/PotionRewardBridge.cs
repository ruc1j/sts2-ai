using System.Text.Json.Serialization;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Screens;
using MegaCrit.Sts2.Core.AutoSlay.Helpers;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Potions;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Rewards;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Nodes.Screens.Map;
using MegaCrit.Sts2.Core.Nodes.Screens.Overlays;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Rewards;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Ai;

[HarmonyPatch(typeof(RewardsScreenHandler), nameof(RewardsScreenHandler.HandleAsync))]
internal static class RewardsScreenHandlerPatch
{
    private static bool Prefix(Rng random, CancellationToken ct, ref Task __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent"))
            return true;
        __result = PotionRewardBridge.Run(random, ct);
        return false;
    }
}

/// <summary>
/// Replaces the stock rewards handler, which skips a PotionReward outright whenever the belt is
/// full (RewardsScreenHandler filters on <c>!(b.Reward is PotionReward) || hasPotionSlots</c>) -
/// the reward is then left on the floor with no decision reaching the agent at all. Everything
/// else here mirrors the stock drain loop; the only addition is asking the agent whether to
/// discard a held potion to make room.
/// </summary>
internal static class PotionRewardBridge
{
    private sealed record PotionRewardAction(
        int Seq,
        string Type,
        int Index,
        [property: JsonPropertyName("potion_id")] string? PotionId,
        [property: JsonPropertyName("decision_source")] string? DecisionSource,
        [property: JsonPropertyName("decision_reason")] string? DecisionReason) : IAgentAction;

    public static async Task Run(Rng random, CancellationToken ct)
    {
        AutoSlayLog.EnterScreen("NRewardsScreen");
        var screen = AutoSlayer.GetCurrentScreen<NRewardsScreen>();
        var attempted = new HashSet<NRewardButton>();
        while (true)
        {
            ct.ThrowIfCancellationRequested();
            var player = LocalContext.GetMe(RunManager.Instance.DebugOnlyGetState());
            var button = UiHelper.FindAll<NRewardButton>(screen)
                .FirstOrDefault(candidate => candidate.IsEnabled && !attempted.Contains(candidate));
            if (button == null)
                break;
            if (button.Reward is PotionReward potionReward && player is { HasOpenPotionSlots: false })
            {
                if (!await MakeRoom(player, potionReward, ct))
                {
                    // The agent kept its belt, so leave this reward alone exactly as the stock
                    // handler would and move on to the next button.
                    attempted.Add(button);
                    continue;
                }
            }
            attempted.Add(button);
            AutoSlayLog.Action("Clicking reward button: " + (button.Reward?.GetType().Name ?? "unknown"));
            await UiHelper.Click(button);
            await Task.Delay(500, ct);
            var overlay = NOverlayStack.Instance?.Peek();
            if (overlay != null && overlay != screen)
            {
                AutoSlayLog.Action("Child screen opened, returning to drain loop");
                AutoSlayLog.ExitScreen("NRewardsScreen");
                return;
            }
        }
        var proceed = UiHelper.FindFirst<NProceedButton>(screen);
        if (proceed != null)
        {
            AutoSlayLog.Action("Clicking proceed");
            await UiHelper.Click(proceed);
            try
            {
                await WaitHelper.Until(
                    () => !GodotObject.IsInstanceValid(screen) || NOverlayStack.Instance?.Peek() != screen || (NMapScreen.Instance?.IsOpen ?? false),
                    ct,
                    TimeSpan.FromSeconds(10),
                    "Rewards screen did not close or map did not open after clicking proceed");
            }
            catch (TimeoutException)
            {
                // The stock handler aborts the whole run here. Proceed can legitimately be refused
                // while an unclaimed reward is still pending (seen once when the card reward screen
                // re-opened NRewardsScreen), and the run was healthy at Act 2 floor 11 when it died.
                // Returning hands the screen back to the drain loop for another pass; if it really
                // is stuck, AutoSlayer's own 30s watchdog still ends the run.
                AutoSlayLog.Action("Proceed did not close the rewards screen; returning to drain loop");
            }
        }
        AutoSlayLog.ExitScreen("NRewardsScreen");
    }

    /// <summary>Asks the agent whether to discard a held potion; true once a slot is free.</summary>
    private static async Task<bool> MakeRoom(
        MegaCrit.Sts2.Core.Entities.Players.Player player, PotionReward reward, CancellationToken ct)
    {
        var held = player.Potions.ToArray();
        if (!player.CanRemovePotions || held.Length == 0 || reward.Potion == null)
            return false;
        var run = RunManager.Instance.DebugOnlyGetState() ?? throw new InvalidOperationException("run state unavailable");
        int seq = AgentIo.NextSequence();
        AgentIo.WriteObservation(new
        {
            seq,
            terminal = false,
            phase = "potion_reward",
            run = new { act = run.CurrentActIndex, floor = run.ActFloor, seed = run.Rng.StringSeed },
            player = new { hp = player.Creature.CurrentHp, max_hp = player.Creature.MaxHp },
            offered = new { id = reward.Potion.Id.ToString() },
            potions = held.Select((potion, index) => new { index, id = potion.Id.ToString() }),
            legal_actions = held
                .Select((potion, index) => (object)new { type = "discard", index, potion_id = potion.Id.ToString() })
                .Append(new { type = "skip", index = -1, potion_id = (string?)null }),
        });
        var action = await AgentIo.AwaitAction<PotionRewardAction>(seq, ct);
        AgentIo.Trace(new
        {
            seq,
            phase = "potion_reward",
            action.Type,
            action.Index,
            potion_id = action.PotionId,
            offered = reward.Potion.Id.ToString(),
            decision_source = action.DecisionSource,
            decision_reason = action.DecisionReason,
        });
        if (action.Type != "discard")
            return false;
        if (action.Index < 0 || action.Index >= held.Length || held[action.Index].Id.ToString() != action.PotionId)
            throw new InvalidOperationException($"illegal potion discard: {action.Index} {action.PotionId}");
        await PotionCmd.Discard(held[action.Index]);
        await WaitHelper.Until(() => player.HasOpenPotionSlots, ct, TimeSpan.FromSeconds(5), "discarded potion did not free a slot");
        return true;
    }
}
