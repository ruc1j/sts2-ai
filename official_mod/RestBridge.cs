using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Rooms;
using MegaCrit.Sts2.Core.AutoSlay.Helpers;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.RestSite;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.Overlays;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Ai;

[HarmonyPatch(typeof(RestSiteRoomHandler), nameof(RestSiteRoomHandler.HandleAsync))]
internal static class RestSiteRoomHandlerPatch
{
    private static bool Prefix(CancellationToken ct, ref Task __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent"))
            return true;
        __result = RestBridge.Run(ct);
        return false;
    }
}

internal static class RestBridge
{
    private sealed record RestAction(int Seq, string Type, int Index, string OptionId) : IAgentAction;

    public static async Task Run(CancellationToken ct)
    {
        var root = ((Godot.SceneTree)Godot.Engine.GetMainLoop()).Root;
        var room = await WaitHelper.ForNode<NRestSiteRoom>(root, "/root/Game/RootSceneContainer/Run/RoomContainer/RestSiteRoom", ct);
        var buttons = UiHelper.FindAll<NRestSiteButton>(room).Where(button => button.Option.IsEnabled).ToArray();
        var run = RunManager.Instance.DebugOnlyGetState() ?? throw new InvalidOperationException("run state unavailable");
        var player = run.Players[0];
        int seq = AgentIo.NextSequence();
        AgentIo.WriteObservation(new
        {
            seq,
            terminal = false,
            phase = "rest",
            run = new { act = run.CurrentActIndex, floor = run.ActFloor, seed = run.Rng.StringSeed },
            player = new { hp = player.Creature.CurrentHp, max_hp = player.Creature.MaxHp },
            legal_actions = buttons.Select((button, index) => new
            {
                type = "rest",
                index,
                option_id = button.Option.OptionId,
                option_type = button.Option.GetType().Name,
            }),
        });
        var action = await AgentIo.AwaitAction<RestAction>(seq, ct);
        if (action.Type != "rest" || action.Index < 0 || action.Index >= buttons.Length || buttons[action.Index].Option.OptionId != action.OptionId)
            throw new InvalidOperationException($"illegal rest action: {action.Index} {action.OptionId}");
        AgentIo.Trace(new { seq, phase = "rest", action.Type, action.Index, option_id = action.OptionId, hp = player.Creature.CurrentHp });
        await UiHelper.Click(buttons[action.Index]);
        var proceed = room.ProceedButton;
        await WaitHelper.Until(() => proceed.IsEnabled || NOverlayStack.Instance?.ScreenCount > 0, ct, TimeSpan.FromSeconds(10), "rest option did not respond");
        if (NOverlayStack.Instance?.ScreenCount == 0)
            await UiHelper.Click(proceed);
    }
}
