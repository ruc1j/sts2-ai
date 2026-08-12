using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Rooms;
using MegaCrit.Sts2.Core.AutoSlay.Helpers;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Nodes.Events;
using MegaCrit.Sts2.Core.Random;

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
}
