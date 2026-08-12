using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Modding;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Saves;
using System.Text.Json;

namespace Sts2Ai;

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
        string seed = CommandLineHelper.GetValue("seed") ?? "FV2EVHXLCW";
        string? log = CommandLineHelper.GetValue("log-file");
        _slayer = new AutoSlayer();
        _slayer.Start(seed, log);
        if (CommandLineHelper.GetValue("stop-after-act") == "1")
            _ = TaskHelper.RunSafely(StopAfterActOne(seed));
    }

    private static async Task StopAfterActOne(string seed)
    {
        RunState? run;
        while ((run = RunManager.Instance.DebugOnlyGetState()) is null || run.CurrentActIndex < 1)
            await Task.Delay(100);

        var player = run.Players[0];
        var result = new
        {
            game_version = "v0.107.1",
            seed,
            character = player.Character.Id.ToString(),
            act_1_complete = true,
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
    private static void Prefix(ref CharacterModel character) => character = ModelDb.Character<Ironclad>();
}
