using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Modding;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Platform.Steam;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Saves;
using MegaCrit.Sts2.Core.Timeline;
using MegaCrit.Sts2.Core.Timeline.Epochs;
using System.Text.Json;
using System.Reflection;

namespace Sts2Ai;

[HarmonyPatch]
internal static class DisableSteamCloudVoidWritesPatch
{
    private static IEnumerable<MethodBase> TargetMethods() => typeof(SteamRemoteSaveStore)
        .GetMethods()
        .Where(method => method.ReturnType == typeof(void) && method.Name is
            "WriteFile" or "DeleteFile" or "RenameFile" or "DeleteDirectory" or "ForgetFile" or "BeginSaveBatch" or "EndSaveBatch" or "SetLastModifiedTime");

    private static bool Prefix() => false;
}

[HarmonyPatch]
internal static class DisableSteamCloudAsyncWritesPatch
{
    private static IEnumerable<MethodBase> TargetMethods() => typeof(SteamRemoteSaveStore)
        .GetMethods()
        .Where(method => method.ReturnType == typeof(Task) && method.Name == "WriteFileAsync");

    private static bool Prefix(ref Task __result)
    {
        __result = Task.CompletedTask;
        return false;
    }
}

[ModInitializer(nameof(Initialize))]
public static class Entry
{
    private static AutoSlayer? _slayer;

    public static void Initialize()
    {
        if (!CommandLineHelper.HasArg("sts2ai-autoslay"))
            return;

        new Harmony("sts2-ai.official").PatchAll();
        TaskHelper.RunSafely(StartWhenReady());
    }

    private static async Task StartWhenReady()
    {
        while (SaveManager.Instance.PrefsSave is null)
            await Task.Delay(100);
        if (CommandLineHelper.HasArg("unlock-ironclad-epochs"))
        {
            SaveManager.Instance.ObtainEpochOverride(EpochModel.GetId<Ironclad2Epoch>(), EpochState.Revealed);
            SaveManager.Instance.ObtainEpochOverride(EpochModel.GetId<Ironclad3Epoch>(), EpochState.Revealed);
            SaveManager.Instance.ObtainEpochOverride(EpochModel.GetId<Ironclad4Epoch>(), EpochState.Revealed);
            SaveManager.Instance.ObtainEpochOverride(EpochModel.GetId<Ironclad5Epoch>(), EpochState.Revealed);
            SaveManager.Instance.ObtainEpochOverride(EpochModel.GetId<Ironclad6Epoch>(), EpochState.Revealed);
            SaveManager.Instance.ObtainEpochOverride(EpochModel.GetId<Ironclad7Epoch>(), EpochState.Revealed);
        }
        string seed = CommandLineHelper.GetValue("seed") ?? "FV2EVHXLCW";
        string? log = CommandLineHelper.GetValue("log-file");
        _slayer = new AutoSlayer();
        _slayer.Start(seed, log);
        if (int.TryParse(CommandLineHelper.GetValue("stop-after-act"), out int stopAfterAct) && stopAfterAct > 0)
            _ = TaskHelper.RunSafely(StopAfterAct(seed, stopAfterAct));
    }

    private static async Task StopAfterAct(string seed, int stopAfterAct)
    {
        RunState? run;
        while ((run = RunManager.Instance.DebugOnlyGetState()) is null ||
            (stopAfterAct < 3 ? run.CurrentActIndex < stopAfterAct : RunManager.Instance.WinTime <= 0))
            await Task.Delay(100);

        var player = run.Players[0];
        var result = new
        {
            game_version = "v0.107.1",
            seed = run.Rng.StringSeed,
            requested_seed = seed,
            character = player.Character.Id.ToString(),
            act_1_complete = run.MapPointHistory.Count > 0,
            act_3_complete = stopAfterAct >= 3 && RunManager.Instance.WinTime > 0,
            acts = run.Acts.Select(act => act.Id.ToString()).ToArray(),
            routes = run.MapPointHistory.Select(route => route.Select(point => point.MapPointType.ToString()).ToArray()).ToArray(),
            route = run.MapPointHistory[0].Select(point => point.MapPointType.ToString()).ToArray(),
            hp = player.Creature.CurrentHp,
            max_hp = player.Creature.MaxHp,
            gold = player.Gold,
            deck = player.Deck.Cards.Select(card => card.Id.ToString()).ToArray(),
            relics = player.Relics.Select(relic => relic.Id.ToString()).ToArray(),
        };
        string path = CommandLineHelper.GetValue("result-file") ?? Path.Combine(Path.GetTempPath(), "sts2-ai-act1.json");
        File.WriteAllText(path, JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
        NGame.Instance?.GetTree().Quit(0);
    }
}

[HarmonyPatch(typeof(NGame), nameof(NGame.StartNewSingleplayerRun))]
internal static class IroncladPatch
{
    private static void Prefix(ref CharacterModel character, ref string seed)
    {
        character = ModelDb.Character<Ironclad>();
        seed = CommandLineHelper.GetValue("seed") ?? seed;
    }
}
