using System.Text.Json;
using System.Text.Json.Serialization;
using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Rooms;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.CardRewardAlternatives;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.GameActions.Multiplayer;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.MonsterMoves.Intents;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Models.Potions;
using MegaCrit.Sts2.Core.Models.Powers;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.TestSupport;

namespace Sts2Ai;

[HarmonyPatch(typeof(CombatRoomHandler), nameof(CombatRoomHandler.HandleAsync))]
internal static class CombatRoomHandlerPatch
{
    private static int _handled;

    internal static bool ReachedAgentLimit => _handled >= int.Parse(CommandLineHelper.GetValue("agent-max-combats") ?? "1");

    private static bool Prefix(Rng random, CancellationToken ct, ref Task __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent") || _handled++ >= int.Parse(CommandLineHelper.GetValue("agent-max-combats") ?? "1"))
            return true;
        __result = CombatBridge.Run(ct);
        return false;
    }
}

[HarmonyPatch(typeof(CardSelectCmd), nameof(CardSelectCmd.FromChooseACardScreen))]
internal static class PotionChooseCardPatch
{
    private static bool Prefix(PlayerChoiceContext context, IReadOnlyList<CardModel> cards, bool canSkip, ref Task<CardModel?> __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent"))
            return true;

        var curseCards = cards.All(card => card.Id.ToString() is "CARD.MIND_ROT" or "CARD.SLOTH" or "CARD.DISINTEGRATION" or "CARD.WASTE_AWAY");
        CardModel? selected = null;
        if (curseCards && cards.Any(card => card.Id.ToString() == "CARD.WASTE_AWAY") && cards.Any(card => card.Id.ToString() == "CARD.DISINTEGRATION"))
            selected = cards.First(card => card.Id.ToString() == "CARD.WASTE_AWAY");
        else if (context.LastInvolvedModel is PowerPotion)
            selected = cards.FirstOrDefault(card => card.EnergyCost.GetAmountToSpend() <= (card.Owner.PlayerCombatState?.Energy ?? 0));
        else if (context.LastInvolvedModel is ColorlessPotion or AttackPotion or SkillPotion)
            selected = cards.FirstOrDefault();
        if (selected is null && context.LastInvolvedModel is not (PowerPotion or ColorlessPotion or AttackPotion or SkillPotion))
            return true;
        __result = Task.FromResult(selected ?? (canSkip ? null : cards.FirstOrDefault()));
        return false;
    }
}

internal static class CombatBridge
{
    private sealed record AgentAction(
        int Seq,
        string Type,
        [property: JsonPropertyName("hand_index")] int? HandIndex,
        [property: JsonPropertyName("upgrade_hand_index")] int? UpgradeHandIndex,
        [property: JsonPropertyName("card_id")] string? CardId,
        [property: JsonPropertyName("target_id")] uint? TargetId,
        [property: JsonPropertyName("potion_index")] int? PotionIndex,
        [property: JsonPropertyName("potion_id")] string? PotionId,
        [property: JsonPropertyName("simulations")] int? Simulations,
        [property: JsonPropertyName("search_value")] double? SearchValue) : IAgentAction;

    public static async Task Run(CancellationToken ct)
    {
        while (!CombatManager.Instance.IsInProgress)
            await Task.Delay(50, ct);

        var run = RunManager.Instance.DebugOnlyGetState() ?? throw new InvalidOperationException("run state unavailable");
        var player = LocalContext.GetMe(run) ?? throw new InvalidOperationException("local player unavailable");
        while (CombatManager.Instance.IsInProgress)
        {
            while (CombatManager.Instance.IsInProgress && player.PlayerCombatState?.Phase != PlayerTurnPhase.Play)
                await Task.Delay(50, ct);
            if (!CombatManager.Instance.IsInProgress)
                break;

            int seq = AgentIo.NextSequence();
            var action = await Exchange(run, player, seq, ct);
            var combat = CombatManager.Instance.DebugOnlyGetState()!;
            AgentIo.Trace(new { seq = action.Seq, phase = "combat", turn = player.PlayerCombatState!.TurnNumber, player_hp = player.Creature.CurrentHp, action.Type, hand_index = action.HandIndex, upgrade_hand_index = action.UpgradeHandIndex, card_id = action.CardId, potion_index = action.PotionIndex, potion_id = action.PotionId, potions = player.Potions.Select(potion => potion.Id.ToString()), target_id = action.TargetId, simulations = action.Simulations, search_value = action.SearchValue, enemies = combat.Enemies.Select(enemy => new { id = enemy.ModelId.ToString(), hp = enemy.CurrentHp, powers = enemy.Powers.Select(power => new { id = power.Id.ToString(), amount = power.Amount }) }) });
            using var selector = CreateUpgradeSelector(player, action);
            if (action.Type == "end_turn")
            {
                RunManager.Instance.ActionQueueSynchronizer.RequestEnqueue(new EndPlayerTurnAction(player, player.PlayerCombatState!.TurnNumber));
            }
            else if (action.Type == "card" && action.HandIndex is int handIndex)
            {
                var hand = player.PlayerCombatState!.Hand.Cards;
                if (handIndex < 0 || handIndex >= hand.Count)
                    throw new InvalidOperationException($"invalid hand index: {handIndex}");
                if (action.CardId != hand[handIndex].Id.ToString())
                    throw new InvalidOperationException($"card reference changed: {action.CardId} != {hand[handIndex].Id}");
                Creature? target = action.TargetId is uint targetId ? player.Creature.CombatState?.GetCreature(targetId) : null;
                if (!hand[handIndex].TryManualPlay(target))
                    throw new InvalidOperationException($"illegal card action: {handIndex} -> {action.TargetId}");
            }
            else if (action.Type == "potion" && action.PotionIndex is int potionIndex)
            {
                var potion = player.GetPotionAtSlotIndex(potionIndex) ?? throw new InvalidOperationException($"empty potion slot: {potionIndex}");
                if (action.PotionId != potion.Id.ToString() || potion.Usage.ToString() == "Automatic" || potion.IsQueued || !potion.PassesCustomUsabilityCheck)
                    throw new InvalidOperationException($"invalid potion action: {action.PotionId}");
                Creature? target = action.TargetId is uint targetId ? combat.GetCreature(targetId) : null;
                if (action.TargetId is null && potion.IsValidTarget(player.Creature))
                    target = player.Creature;
                if (!potion.IsValidTarget(target))
                    throw new InvalidOperationException($"illegal potion target: {potionIndex} -> {action.TargetId}");
                potion.EnqueueManualUse(target);
            }
            else
            {
                throw new InvalidOperationException($"unknown agent action: {action.Type}");
            }
            await RunManager.Instance.ActionExecutor.FinishedExecutingActions();
        }
        AgentIo.Trace(new { seq = AgentIo.NextSequence(), phase = "combat_end", won = player.Creature.CurrentHp > 0, hp = player.Creature.CurrentHp });
        if (CommandLineHelper.GetValue("stop-after-agent") == "1" && CombatRoomHandlerPatch.ReachedAgentLimit)
        {
            int seq = AgentIo.NextSequence();
            AgentIo.WriteObservation(new { seq, terminal = true });
            AgentIo.Trace(new { seq, terminal = true });
            NGame.Instance?.GetTree().Quit(0);
        }
    }

    private static async Task<AgentAction> Exchange(RunState run, MegaCrit.Sts2.Core.Entities.Players.Player player, int seq, CancellationToken ct)
    {
        var combat = CombatManager.Instance.DebugOnlyGetState() ?? throw new InvalidOperationException("combat state unavailable");
        var hand = player.PlayerCombatState!.Hand.Cards;
        var legal = new List<object>();
        for (int i = 0; i < hand.Count; i++)
        {
            if (hand[i].CanPlayTargeting(null))
                legal.Add(new { type = "card", hand_index = i, card_id = hand[i].Id.ToString(), target_id = (uint?)null });
            foreach (Creature target in combat.Creatures.Where(hand[i].CanPlayTargeting))
                legal.Add(new { type = "card", hand_index = i, card_id = hand[i].Id.ToString(), target_id = target.CombatId });
        }
        for (int i = 0; i < player.PotionSlots.Count; i++)
        {
            var potion = player.PotionSlots[i];
            if (potion is null || potion.Usage.ToString() == "Automatic" || potion.IsQueued || !potion.PassesCustomUsabilityCheck)
                continue;
            if (potion.IsValidTarget(null))
                legal.Add(new { type = "potion", potion_index = i, potion_id = potion.Id.ToString(), target_id = (uint?)null });
            if (potion.IsValidTarget(player.Creature))
                legal.Add(new { type = "potion", potion_index = i, potion_id = potion.Id.ToString(), target_id = (uint?)null });
            foreach (Creature target in combat.Creatures.Where(target => target != player.Creature && potion.IsValidTarget(target)))
                legal.Add(new { type = "potion", potion_index = i, potion_id = potion.Id.ToString(), target_id = target.CombatId });
        }
        legal.Add(new { type = "end_turn", hand_index = (int?)null, card_id = (string?)null, target_id = (uint?)null });
        AgentIo.WriteObservation(new
        {
            seq,
            terminal = false,
            phase = "combat",
            turn = player.PlayerCombatState.TurnNumber,
            run = new { act = run.CurrentActIndex, floor = run.ActFloor },
            player = new
            {
                hp = player.Creature.CurrentHp,
                max_hp = player.Creature.MaxHp,
                block = player.Creature.Block,
                energy = player.PlayerCombatState.Energy,
                max_energy = player.PlayerCombatState.MaxEnergy,
                powers = player.Creature.Powers.Select(p => new { id = p.Id.ToString(), amount = p.Amount, facing = p is SurroundedPower surrounded ? surrounded.Facing.ToString() : null }),
                relics = player.Relics.Select(r => r.Id.ToString()),
                upgraded_cards = player.Deck.Cards.Concat(player.PlayerCombatState.AllCards).Where(card => card.CurrentUpgradeLevel > 0).Select(card => card.Id.ToString()),
            },
            hand = hand.Select((card, index) => new
            {
                index,
                id = card.Id.ToString(),
                cost = card.EnergyCost.GetWithModifiers(CostModifiers.All),
                upgrade = card.CurrentUpgradeLevel,
                type = card.Type.ToString(),
                rarity = card.Rarity.ToString(),
                pool = card.Pool.Id.ToString(),
                vars = card.DynamicVars.Select(variable => new { id = variable.Key, value = variable.Value.PreviewValue }),
                target = card.TargetType.ToString(),
            }),
            draw_pile = player.PlayerCombatState.DrawPile.Cards.Select(card => card.Id.ToString()),
            discard_pile = player.PlayerCombatState.DiscardPile.Cards.Select(card => card.Id.ToString()),
            exhaust_pile = player.PlayerCombatState.ExhaustPile.Cards.Select(card => card.Id.ToString()),
            potions = player.PotionSlots.Select((potion, index) => potion is null ? null : new { index, id = potion.Id.ToString(), usage = potion.Usage.ToString(), target = potion.TargetType.ToString() }),
            enemies = combat.Enemies.Select(enemy => new
            {
                combat_id = enemy.CombatId,
                id = enemy.ModelId.ToString(),
                hp = enemy.CurrentHp,
                max_hp = enemy.MaxHp,
                block = enemy.Block,
                slot = enemy.SlotName,
                move = enemy.Monster?.NextMove.Id,
                history = enemy.Monster?.MoveStateMachine?.StateLog.Where(state => state.IsMove).Select(state => state.Id),
                intents = enemy.Monster?.NextMove.Intents.Select(intent => Intent(intent, combat.PlayerCreatures, enemy)),
                powers = enemy.Powers.Select(p => new { id = p.Id.ToString(), amount = p.Amount }),
            }),
            legal_actions = legal,
        });
        return await AgentIo.AwaitAction<AgentAction>(seq, ct);
    }

    private static IDisposable? CreateUpgradeSelector(MegaCrit.Sts2.Core.Entities.Players.Player player, AgentAction action)
    {
        if (action.UpgradeHandIndex is not int upgradeIndex)
            return null;
        if (action.Type != "card" || action.HandIndex is not int handIndex)
            throw new InvalidOperationException("Armaments target requires a card action");
        var hand = player.PlayerCombatState!.Hand.Cards;
        if (upgradeIndex < 0 || upgradeIndex >= hand.Count || upgradeIndex == handIndex || !hand[upgradeIndex].IsUpgradable)
            throw new InvalidOperationException($"invalid Armaments target: {upgradeIndex}");
        return CardSelectCmd.PushSelector(new ExactCardSelector(hand[upgradeIndex]));
    }

    private static object Intent(AbstractIntent intent, IReadOnlyList<Creature> targets, Creature owner)
    {
        if (intent is AttackIntent attack)
            return new { type = intent.IntentType.ToString(), damage = attack.GetSingleDamage(targets, owner), repeats = attack.Repeats };
        return new { type = intent.IntentType.ToString(), damage = 0, repeats = 0 };
    }

    private sealed class ExactCardSelector : ICardSelector
    {
        private readonly CardModel _selected;

        public ExactCardSelector(CardModel selected) => _selected = selected;

        public Task<IEnumerable<CardModel>> GetSelectedCards(IEnumerable<CardModel> options, int minSelect, int maxSelect)
        {
            var selected = options.FirstOrDefault(card => ReferenceEquals(card, _selected));
            return Task.FromResult<IEnumerable<CardModel>>(selected is null ? Array.Empty<CardModel>() : [selected]);
        }

        public CardRewardSelection GetSelectedCardReward(IReadOnlyList<CardCreationResult> options, IReadOnlyList<CardRewardAlternative> alternatives) => default;
    }

}

internal interface IAgentAction
{
    int Seq { get; }
}

internal static class AgentIo
{
    private static int _sequence = -1;
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        WriteIndented = true,
    };
    private static readonly JsonSerializerOptions TraceOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower };

    public static int NextSequence() => Interlocked.Increment(ref _sequence);

    public static void WriteObservation(object value)
    {
        string path = CommandLineHelper.GetValue("bridge-observation") ?? throw new InvalidOperationException("bridge-observation missing");
        WriteJson(path, value);
    }

    public static void WriteJson(string path, object value)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        string temp = path + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(value, JsonOptions));
        for (int attempt = 0; ; attempt++)
        {
            try
            {
                File.Move(temp, path, true);
                return;
            }
            catch (Exception error) when (error is IOException or UnauthorizedAccessException && attempt < 200)
            {
                Thread.Sleep(5);
            }
        }
    }

    public static async Task<T> AwaitAction<T>(int seq, CancellationToken ct) where T : class, IAgentAction
    {
        string path = CommandLineHelper.GetValue("bridge-action") ?? throw new InvalidOperationException("bridge-action missing");
        DateTime deadline = DateTime.UtcNow.AddMinutes(2);
        while (DateTime.UtcNow < deadline)
        {
            ct.ThrowIfCancellationRequested();
            if (File.Exists(path))
            {
                try
                {
                    var action = JsonSerializer.Deserialize<T>(File.ReadAllText(path), JsonOptions);
                    if (action?.Seq == seq)
                        return action;
                }
                catch (IOException) { }
                catch (JsonException) { }
            }
            await Task.Delay(25, ct);
        }
        throw new TimeoutException($"agent did not answer observation {seq}");
    }

    public static void Trace(object value)
    {
        string? path = CommandLineHelper.GetValue("bridge-trace");
        if (path is null)
            return;
        File.AppendAllText(path, JsonSerializer.Serialize(value, TraceOptions) + Environment.NewLine);
    }
}
