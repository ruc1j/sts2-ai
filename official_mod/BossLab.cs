using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;
using MegaCrit.Sts2.Core.Assets;
using MegaCrit.Sts2.Core.AutoSlay;
using MegaCrit.Sts2.Core.AutoSlay.Helpers;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.Entities.Players;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Map;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Characters;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.Rooms;
using MegaCrit.Sts2.Core.Saves.Runs;
using MegaCrit.Sts2.Core.Unlocks;

namespace Sts2Ai;

/// <summary>
/// Fixed-entry boss lab: builds a run state from a recorded boss entry (deck with enchantments,
/// HP, relics, potions, entry powers, run seed, floors walked), jumps straight into the boss
/// encounter with <c>RunManager.EnterRoomDebug</c>, lets the existing agent bridge play the fight,
/// and writes one JSONL result line per trial.
///
/// The Act 2 boss (THE_INSATIABLE, floor 16 of the 17-row Hive maps) was the first target; the
/// Act 3 boss (QUEEN + Torch Head Amalgam, floor 15 of the 15-row Glory maps) uses the same path
/// with act_index 2 and the plan's own act_floor / history_per_act, so nothing here is Act-specific
/// beyond the encounter id.
///
/// One trial per game process in this version: the boss fight's ending (reward screens on a win,
/// the game over screen on a loss) is not driven here, so the trial records the result as soon as
/// <c>CombatManager.IsInProgress</c> goes false and quits the process, exactly like
/// <see cref="Entry"/>’s stop-after-act path does. The runner script relaunches the game with the
/// next trial index; see .dsh/bosslab_notes.md for the in-process loop that should replace this
/// once the post-combat screens are observed in-game.
///
/// Injection coverage (what a trial can carry): card id + upgrade + enchantment (id and amount),
/// relic ids, potion ids, HP / max HP, walked-floor counts, and player powers as residuals
/// (BossLab.ApplyEntryPowers). Potions are injected as models, so the container's holders have to be
/// rebuilt (BossLab.RefreshPotionUi) or using one throws in the game's UI layer. What it cannot
/// carry: a relic's own run state (Ember Tea's used-up flag, Girya's lift count) - those specs are
/// excluded by the plan generator instead - and the "cards played this turn" counters, so an entry
/// observation taken after the fight had already begun plays its first recorded decision with clean
/// counters.
///
/// Why these game APIs (decompiled v0.107.1 evidence, see .dsh/bosslab_notes.md):
/// - RunState.CreateForNewRun accepts an arbitrary seed string: Runs/RunState.cs:272-274 (RunRngSet(seed)).
/// - UnlockState.all avoids depending on the player's progress save: Unlocks/UnlockState.cs:32-34.
/// - RunManager.SetUpNewSingleplayer(state, shouldSave: false) writes no save file: Runs/RunManager.cs:236-244.
/// - The scene/act setup order mirrors Nodes.Debug/NSceneBootstrapper.cs:101-113 and Nodes/NGame.cs:1158-1166.
/// - RunState.TotalFloor is the MapPointHistory entry count: Runs/RunState.cs:158, which is what seeds
///   the encounter's monster generation RNG (Models/EncounterModel.cs:266-269), so padding the history
///   to the recorded floor reproduces the same boss composition.
/// - EnterRoomDebug overrides the room type from the encounter model: Runs/RunManager.cs:995-997, and
///   clears screens/exits rooms before entering: Runs/RunManager.cs:990-1035.
/// - CardModel.FromSerializable applies SerializableCard.Enchantment through EnchantInternal +
///   ModifyCard + FinalizeUpgradeInternal: Models/CardModel.cs:2216-2240, so an enchantment set on
///   the serializable card survives into the deck.
/// - PowerCmd.Apply is a direct async apply (not a queued action): Commands/PowerCmd.cs:67, so it can
///   be awaited from this driver after room entry to land a residual power before the first decision.
/// - A boss composition that includes a MinionPower carrier (the Queen's Torch Head Amalgam) needs
///   no special case: EnterRoomDebug builds the formation from the encounter, and the secondary
///   enemy auto-dies when the primary does (Entities/Creatures/Creature.cs:245-268).
/// </summary>
public static class BossLab
{
    private static readonly JsonSerializerOptions JsonRead = new()
    {
        PropertyNameCaseInsensitive = true,
        ReadCommentHandling = JsonCommentHandling.Skip,
        AllowTrailingCommas = true,
    };

    public static bool Enabled => CommandLineHelper.HasArg("sts2ai-bosslab");

    private static string Value(string name, string fallback = "") => CommandLineHelper.GetValue(name) ?? fallback;

    /// <summary>Entry point, called from <see cref="Entry"/> instead of AutoSlay when the lab flag is set.</summary>
    public static async Task RunAsync()
    {
        string planPath = Value("bosslab-plan");
        int index = int.TryParse(Value("bosslab-trial"), out int parsed) ? parsed : 0;
        string outPath = Value("bosslab-out", Path.Combine(Path.GetTempPath(), "sts2ai-bosslab.jsonl"));

        LabTrial? trial = null;
        string? error = null;
        LabResult? result = null;
        var watch = Stopwatch.StartNew();
        try
        {
            LabPlan? plan = JsonSerializer.Deserialize<LabPlan>(File.ReadAllText(planPath), JsonRead);
            if (plan is null || plan.Trials is null || index >= plan.Trials.Count)
                throw new InvalidOperationException($"plan has no trial {index} (file {planPath})");
            trial = plan.Trials[index];
            result = await RunTrial(trial, index);
        }
        catch (Exception e)
        {
            error = e.ToString();
            AutoSlayLog.Error($"[BossLab] trial {index} failed: {e}");
        }
        watch.Stop();

        AppendResult(outPath, new LabLine
        {
            TrialIndex = index,
            TrialId = trial?.TrialId ?? "",
            SpecId = trial?.SpecId ?? "",
            Encounter = trial?.Encounter ?? "",
            EffectiveSeed = trial is null ? "" : EffectiveSeed(trial),
            ElapsedMs = watch.ElapsedMilliseconds,
            Error = error,
            Result = result,
        });
        AutoSlayLog.Info($"[BossLab] trial {index} done in {watch.ElapsedMilliseconds} ms, quitting");
        await Task.Delay(250);
        NGame.Instance?.GetTree().Quit(0);
    }

    private static async Task<LabResult> RunTrial(LabTrial trial, int index)
    {
        var acts = ActModel.GetDefaultList().Select(act => act.ToMutable()).ToList();
        if (trial.ActIndex < 0 || trial.ActIndex >= acts.Count)
            throw new InvalidOperationException($"act_index {trial.ActIndex} outside the default act list");
        var character = ModelDb.GetById<CharacterModel>(
            new ModelId(ModelId.SlugifyCategory<CharacterModel>(), Entry(trial.Character, "CHARACTER")));

        string seed = EffectiveSeed(trial);
        var runState = RunState.CreateForNewRun(
            new List<Player> { Player.CreateForNewRun(character, UnlockState.all, 1UL) },
            acts, new List<ModifierModel>(), GameMode.Standard, trial.Ascension, seed);
        RunManager.Instance.SetUpNewSingleplayer(runState, shouldSave: false, dailyTime: null);

        await PreloadManager.LoadRunAssets(new List<CharacterModel> { character });
        await PreloadManager.LoadActAssets(acts[trial.ActIndex]);
        await RunManager.Instance.FinalizeStartingRelics();
        RunManager.Instance.Launch();
        var game = NGame.Instance ?? throw new InvalidOperationException("NGame.Instance is unavailable");
        game.RootSceneContainer.SetCurrentScene(NRun.Create(runState));
        await RunManager.Instance.SetActInternal(trial.ActIndex);

        var player = runState.Players[0];
        ApplyPlayerState(player, trial);

        // Pad the walked floors so TotalFloor (Runs/RunState.cs:158) matches the recorded entry, which
        // is what the encounter's monster generation RNG is seeded from (Models/EncounterModel.cs:266-269).
        for (int act = 0; act < trial.HistoryPerAct.Count; act++)
        {
            runState.CurrentActIndex = act;
            for (int floor = 0; floor < trial.HistoryPerAct[act]; floor++)
                runState.AppendToMapPointHistory(MapPointType.Monster, RoomType.Monster, null);
        }
        runState.CurrentActIndex = trial.ActIndex;
        runState.ActFloor = trial.ActFloor;

        var encounter = ModelDb.GetById<EncounterModel>(
            new ModelId(ModelId.SlugifyCategory<EncounterModel>(), Entry(trial.Encounter, "ENCOUNTER"))).ToMutable();
        AutoSlayLog.Info($"[BossLab] trial {index} seed={seed} act={trial.ActIndex} floor={trial.ActFloor} " +
            $"totalFloor={runState.TotalFloor} deck={player.Deck.Cards.Count} encounter={encounter.Id.Entry}");

        // AutoSlayer installs this selector for the whole run; without it a hand/deck selection card
        // (Burning Pact, Armaments, Headbutt...) waits forever for UI input and the fight never ends.
        using var selectorScope = CardSelectCmd.UseSelector(
            new AutoSlayCardSelector(new Rng((uint)StringHelper.GetDeterministicHashCode(seed))));

        await RunManager.Instance.EnterRoomDebug(RoomType.Boss, MapPointType.Unassigned, encounter, showTransition: false);

        // The potion container builds its holder nodes once, when the run UI initializes (before this
        // driver injects anything), and afterwards only from the `PotionProcured` event, which
        // `AddPotionInternal(silent: true)` deliberately does not raise. With no holder, using an
        // injected potion throws in `NPotionContainer.RemoveUsed` (Nodes/Potions/NPotionContainer.cs:352-357,
        // a `First` over the holders), the potion action dies, the action queue never drains, and the
        // trial hangs until the runner's timeout. Re-initializing the container after the room is up
        // makes it build holders for whatever is in the slots now (Nodes/Potions/NPotionContainer.cs:
        // 197-207 reads `_player.Potions` and calls `Add(potion, isInitialization: true)`).
        RefreshPotionUi(runState);

        // Room entry has now run, so the injected relics' own combat-entry grants have landed. Add
        // only what the recorded entry shows on top of those, before the bridge takes its first look.
        await ApplyEntryPowers(player, trial);

        // AutoSlay is not running in lab mode, so its CombatRoomHandler patch never starts the agent
        // bridge; drive the fight with the same CombatBridge.Run it would have called.
        var bridgeTask = CombatBridge.Run(CancellationToken.None);
        var fightResult = await AwaitFight(player, trial, runState);
        await Task.WhenAny(bridgeTask, Task.Delay(5000));
        return fightResult;
    }

    /// <summary>
    /// Watches the fight from outside the agent bridge and decides the trial's outcome.
    ///
    /// Win/loss comes from the bridge's own <c>combat_end</c> trace record — the same record the
    /// full-run manifests use — because the sampled enemy HP cannot reproduce it: the 200 ms poll
    /// misses the defeat instant, leaving enemy HP &gt; 0 on the last sample and turning a win into
    /// a loss. So after the fight stops we wait briefly for the bridge to append that record
    /// (CombatBridge.cs:215 writes <c>won = player hp &gt; 0 &amp;&amp; !gameOver</c> and <c>hp</c>) and read
    /// it. If no such record lands, fall back to <c>player hp &gt; 0</c>. The player, enemy, and turn
    /// samples stay in the output as reference values only.
    /// </summary>
    private static async Task<LabResult> AwaitFight(Player player, LabTrial trial, RunState runState)
    {
        var result = new LabResult
        {
            EntryPlayerHp = player.Creature.CurrentHp,
            EntryPlayerMaxHp = player.Creature.MaxHp,
            EntryDeckSize = player.Deck.Cards.Count,
            TotalFloorAtEntry = runState.TotalFloor,
        };
        int staleFrames = 0;
        while (!CombatManager.Instance.IsInProgress && staleFrames < 100)
        {
            await Task.Delay(100);
            staleFrames++;
        }
        CombatState? last = null;
        while (CombatManager.Instance.IsInProgress)
        {
            var state = CombatManager.Instance.DebugOnlyGetState();
            if (state is not null)
                last = state;
            await Task.Delay(200);
        }

        result.FinalPlayerHp = player.Creature.CurrentHp;
        result.FinalPlayerMaxHp = player.Creature.MaxHp;
        if (last is not null)
        {
            result.LastObservedTurn = last.Players.Count > 0 ? last.Players[0].PlayerCombatState?.TurnNumber ?? 0 : 0;
            result.EnemyHpLastObserved = last.Enemies
                .Select(enemy => new LabEnemy { Id = enemy.Monster?.Id.ToString() ?? "", Hp = enemy.CurrentHp, MaxHp = enemy.MaxHp })
                .ToList();
        }

        // The bridge flips IsInProgress and appends its combat_end record in the same beat, but the
        // two tasks observe IsInProgress independently, so allow up to 5 s for the record to appear.
        string? tracePath = CommandLineHelper.GetValue("bridge-trace");
        (bool Won, int? Hp)? combatEnd = null;
        for (int attempt = 0; attempt < 20 && combatEnd is null; attempt++)
        {
            combatEnd = ReadLastCombatEnd(tracePath);
            if (combatEnd is null)
                await Task.Delay(250);
        }

        if (combatEnd is not null)
        {
            result.Won = combatEnd.Value.Won;
            result.FinalPlayerHp = combatEnd.Value.Hp ?? result.FinalPlayerHp;
            result.OutcomeSource = "combat_end_trace";
        }
        else
        {
            result.Won = result.FinalPlayerHp > 0;
            result.OutcomeSource = "player_hp_fallback";
            AutoSlayLog.Error($"[BossLab] no combat_end record in {tracePath ?? "<unset>"}; " +
                $"using player hp {result.FinalPlayerHp} to decide win/loss");
        }
        return result;
    }

    /// <summary>
    /// The last <c>combat_end</c> record in the bridge trace, or null if none has been written yet.
    /// Only called after the fight has stopped, so the file is not mid-write on the next poll.
    /// </summary>
    private static (bool Won, int? Hp)? ReadLastCombatEnd(string? tracePath)
    {
        if (tracePath is null || !File.Exists(tracePath))
            return null;
        (bool Won, int? Hp)? last = null;
        foreach (string line in File.ReadLines(tracePath))
        {
            if (!line.Contains("\"combat_end\""))
                continue;
            try
            {
                using var doc = JsonDocument.Parse(line);
                if (!doc.RootElement.TryGetProperty("phase", out var phase) ||
                    phase.ValueKind is not JsonValueKind.String ||
                    phase.GetString() != "combat_end" ||
                    !doc.RootElement.TryGetProperty("won", out var won) ||
                    won.ValueKind is not (JsonValueKind.True or JsonValueKind.False))
                {
                    continue;
                }
                int? hp = doc.RootElement.TryGetProperty("hp", out var hpElement) &&
                    hpElement.TryGetInt32(out int parsed) ? parsed : null;
                last = (won.GetBoolean(), hp);
            }
            catch (JsonException)
            {
                continue;  // a partially written trailing line
            }
        }
        return last;
    }

    private static void ApplyPlayerState(Player player, LabTrial trial)
    {
        foreach (var relic in player.Relics.ToList())
            player.RemoveRelicInternal(relic, silent: true);
        foreach (string id in trial.Relics)
        {
            var model = RelicModel.FromSerializable(new SerializableRelic
            {
                Id = new ModelId(ModelId.SlugifyCategory<RelicModel>(), Entry(id, "RELIC")),
            });
            player.AddRelicInternal(model, -1, silent: true);
        }

        foreach (var potion in player.PotionSlots.ToList())
        {
            if (potion is not null)
                player.DiscardPotionInternal(potion, silent: true);
        }
        for (int slot = 0; slot < trial.Potions.Count && slot < player.MaxPotionCount; slot++)
        {
            var model = PotionModel.FromSerializable(new SerializablePotion
            {
                Id = new ModelId(ModelId.SlugifyCategory<PotionModel>(), Entry(trial.Potions[slot], "POTION")),
                SlotIndex = slot,
            });
            player.AddPotionInternal(model, slot, silent: true);
        }

        player.Deck.Clear(silent: true);
        foreach (LabCard card in trial.Deck)
        {
            // RunState.LoadCard registers the card with the run and sets its owner; a bare
            // CardModel.FromSerializable leaves Owner null, which RunState.Contains dereferences
            // while EnterRoomDebug iterates the hook listeners.
            //
            // The enchantment goes in through the same serializable object: FromSerializable reads
            // `Enchantment` and runs EnchantInternal + ModifyCard + FinalizeUpgradeInternal
            // (CardModel.cs:2216-2240), so the card comes back with the recorded enchantment effect
            // (Nimble / Corrupted / SoulsPower / TezcatarasEmber ...) rather than dropping it.
            var model = player.RunState.LoadCard(new SerializableCard
            {
                Id = new ModelId(ModelId.SlugifyCategory<CardModel>(), Entry(card.Id, "CARD")),
                CurrentUpgradeLevel = card.Upgrade,
                Enchantment = string.IsNullOrEmpty(card.Enchantment) ? null : new SerializableEnchantment
                {
                    Id = new ModelId(ModelId.SlugifyCategory<EnchantmentModel>(),
                                       Entry(card.Enchantment, "ENCHANTMENT")),
                    Amount = card.EnchantmentAmount > 0 ? card.EnchantmentAmount : 1,
                },
            }, player);
            player.Deck.AddInternal(model, -1, silent: true);
        }

        player.Creature.SetMaxHpInternal(trial.MaxHp > 0 ? trial.MaxHp : trial.Hp);
        player.Creature.SetCurrentHpInternal(trial.Hp);
    }

    /// <summary>
    /// Inject the player powers the recorded entry shows but the injected relic list does not
    /// produce by itself. Run after EnterRoomDebug so the relics' own `AfterRoomEntered` grants have
    /// already landed and are not doubled; run before the bridge's first observation so the agent
    /// sees the same state the recorded run saw.
    ///
    /// The plan generator computes each amount as (recorded entry amount - amount the relic list is
    /// expected to grant), so a positive amount here is genuinely leftover state: a power a card put
    /// on the player during an earlier fight, or a relic whose grant is not an entry hook.
    /// </summary>
    private static async Task ApplyEntryPowers(Player player, LabTrial trial)
    {
        foreach (LabPower power in trial.Powers)
        {
            if (power.Amount <= 0)
                continue;
            string id = Entry(power.Id, "POWER");
            await ApplyOnePower(player, id, power.Amount);
        }
        var applied = player.Creature.Powers
            .Select(p => $"{p.Id.Entry}:{p.Amount}");
        AutoSlayLog.Info($"[BossLab] entry powers after injection: [{string.Join(", ", applied)}] " +
            $"requested [{string.Join(", ", trial.Powers.Select(p => $"{p.Id}:{p.Amount}"))}]");
    }

    /// <summary>
    /// Rebuild the on-screen potion holders from the player's current slots. See the call site in
    /// <see cref="RunTrial"/> for why injected potions need this before the agent may use one.
    /// </summary>
    private static void RefreshPotionUi(IRunState runState)
    {
        NRun.Instance?.GlobalUi?.TopBar?.PotionContainer?.Initialize(runState);
    }

    /// <summary>
    /// `PowerCmd.Apply` is generic over the power class, so the ids a plan can name are listed here.
    /// Adding a new power to a plan means adding its case; an unknown id is logged and skipped
    /// rather than thrown, so one unmapped power does not fail an entire trial set.
    /// </summary>
    private static async Task ApplyOnePower(Player player, string id, int amount)
    {
        var context = new ThrowingPlayerChoiceContext();
        var creature = player.Creature;
        switch (id)
        {
            case "STRENGTH_POWER":
                await PowerCmd.Apply<StrengthPower>(context, creature, amount, creature, null, silent: true);
                break;
            case "DEXTERITY_POWER":
                await PowerCmd.Apply<DexterityPower>(context, creature, amount, creature, null, silent: true);
                break;
            case "PLATING_POWER":
                await PowerCmd.Apply<PlatingPower>(context, creature, amount, creature, null, silent: true);
                break;
            case "THORNS_POWER":
                await PowerCmd.Apply<ThornsPower>(context, creature, amount, creature, null, silent: true);
                break;
            case "VIGOR_POWER":
                await PowerCmd.Apply<VigorPower>(context, creature, amount, creature, null, silent: true);
                break;
            case "FEEL_NO_PAIN_POWER":
                await PowerCmd.Apply<FeelNoPainPower>(context, creature, amount, creature, null, silent: true);
                break;
            case "FLAME_BARRIER_POWER":
                await PowerCmd.Apply<FlameBarrierPower>(context, creature, amount, creature, null, silent: true);
                break;
            case "HELLRAISER_POWER":
                await PowerCmd.Apply<HellraiserPower>(context, creature, amount, creature, null, silent: true);
                break;
            case "RUPTURE_POWER":
                await PowerCmd.Apply<RupturePower>(context, creature, amount, creature, null, silent: true);
                break;
            case "RAGE_POWER":
                await PowerCmd.Apply<RagePower>(context, creature, amount, creature, null, silent: true);
                break;
            case "NO_DRAW_POWER":
                await PowerCmd.Apply<NoDrawPower>(context, creature, amount, creature, null, silent: true);
                break;
            default:
                AutoSlayLog.Error($"[BossLab] power {id} has no injection case; entry state will differ " +
                    "from the recorded run");
                break;
        }
    }

    private static string EffectiveSeed(LabTrial trial) =>
        trial.RngOffset == 0 ? trial.RunSeed : $"{trial.RunSeed}-{trial.RngOffset}";

    /// <summary>Strips the "CATEGORY." prefix that the game's own ModelId.ToString() writes.</summary>
    private static string Entry(string fullId, string category)
    {
        string bare = fullId.Contains('.') ? fullId.Split('.', 2)[1] : fullId;
        return bare.ToUpperInvariant();
    }

    private static void AppendResult(string path, LabLine line)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path) ?? ".");
        File.AppendAllText(path, JsonSerializer.Serialize(line, new JsonSerializerOptions
        {
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
        }) + "\n");
    }
}

public class LabPlan
{
    [JsonPropertyName("character")] public string Character { get; set; } = "IRONCLAD";
    [JsonPropertyName("ascension")] public int Ascension { get; set; }
    [JsonPropertyName("trials")] public List<LabTrial> Trials { get; set; } = new();
}

public class LabTrial
{
    [JsonPropertyName("trial_index")] public int TrialIndex { get; set; }
    [JsonPropertyName("trial_id")] public string TrialId { get; set; } = "";
    [JsonPropertyName("spec_id")] public string SpecId { get; set; } = "";
    [JsonPropertyName("encounter")] public string Encounter { get; set; } = "ENCOUNTER.THE_INSATIABLE_BOSS";
    [JsonPropertyName("character")] public string Character { get; set; } = "IRONCLAD";
    [JsonPropertyName("run_seed")] public string RunSeed { get; set; } = "";
    [JsonPropertyName("rng_offset")] public int RngOffset { get; set; }
    [JsonPropertyName("act_index")] public int ActIndex { get; set; } = 1;
    [JsonPropertyName("act_floor")] public int ActFloor { get; set; } = 16;
    [JsonPropertyName("ascension")] public int Ascension { get; set; }
    /// <summary>Walked floors per act index, excluding the boss room itself (EnterRoomDebug adds it).</summary>
    [JsonPropertyName("history_per_act")] public List<int> HistoryPerAct { get; set; } = new();
    [JsonPropertyName("hp")] public int Hp { get; set; }
    [JsonPropertyName("max_hp")] public int MaxHp { get; set; }
    [JsonPropertyName("deck")] public List<LabCard> Deck { get; set; } = new();
    [JsonPropertyName("relics")] public List<string> Relics { get; set; } = new();
    [JsonPropertyName("potions")] public List<string> Potions { get; set; } = new();
    /// <summary>
    /// Powers to inject after room entry. Amounts must already be reduced by whatever the injected
    /// relic list grants on its own, or the power lands twice (the entry-firing relics re-run their
    /// AfterRoomEntered hook here). Relics whose own entry grant depends on run state
    /// (`RELIC.EMBER_TEA`'s IsUsedUp, `RELIC.GIRYA`'s TimesLifted) are handled by excluding those
    /// specs from a plan, not by injection.
    /// </summary>
    [JsonPropertyName("powers")] public List<LabPower> Powers { get; set; } = new();
}

public class LabCard
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("upgrade")] public int Upgrade { get; set; }
    /// <summary>Enchantment id (`ENCHANTMENT.NIMBLE`); empty when the card carries none.</summary>
    [JsonPropertyName("enchantment")] public string Enchantment { get; set; } = "";
    [JsonPropertyName("enchantment_amount")] public int EnchantmentAmount { get; set; } = 1;
}

/// <summary>
/// A player power to inject into the combat after room entry, expressed as the residual amount the
/// relic list does not produce on its own (see BossLab.ApplyEntryPowers).
/// </summary>
public class LabPower
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("amount")] public int Amount { get; set; }
}

public class LabLine
{
    [JsonPropertyName("trial_index")] public int TrialIndex { get; set; }
    [JsonPropertyName("trial_id")] public string TrialId { get; set; } = "";
    [JsonPropertyName("spec_id")] public string SpecId { get; set; } = "";
    [JsonPropertyName("encounter")] public string Encounter { get; set; } = "";
    [JsonPropertyName("effective_seed")] public string EffectiveSeed { get; set; } = "";
    [JsonPropertyName("elapsed_ms")] public long ElapsedMs { get; set; }
    [JsonPropertyName("error")] public string? Error { get; set; }
    [JsonPropertyName("result")] public LabResult? Result { get; set; }
}

public class LabResult
{
    [JsonPropertyName("won")] public bool Won { get; set; }
    /// <summary>Where the win/loss came from: the bridge's combat_end record, or a player-hp fallback.</summary>
    [JsonPropertyName("outcome_source")] public string OutcomeSource { get; set; } = "";
    [JsonPropertyName("entry_player_hp")] public int EntryPlayerHp { get; set; }
    [JsonPropertyName("entry_player_max_hp")] public int EntryPlayerMaxHp { get; set; }
    [JsonPropertyName("entry_deck_size")] public int EntryDeckSize { get; set; }
    [JsonPropertyName("total_floor_at_entry")] public int TotalFloorAtEntry { get; set; }
    [JsonPropertyName("final_player_hp")] public int FinalPlayerHp { get; set; }
    [JsonPropertyName("final_player_max_hp")] public int FinalPlayerMaxHp { get; set; }
    [JsonPropertyName("last_observed_turn")] public int LastObservedTurn { get; set; }
    [JsonPropertyName("enemy_hp_last_observed")] public List<LabEnemy> EnemyHpLastObserved { get; set; } = new();
}

public class LabEnemy
{
    [JsonPropertyName("id")] public string Id { get; set; } = "";
    [JsonPropertyName("hp")] public int Hp { get; set; }
    [JsonPropertyName("max_hp")] public int MaxHp { get; set; }
}
