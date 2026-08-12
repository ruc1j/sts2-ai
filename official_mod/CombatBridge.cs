using System.Text.Json;
using System.Text.Json.Serialization;
using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Rooms;
using MegaCrit.Sts2.Core.Combat;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Creatures;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.MonsterMoves.Intents;
using MegaCrit.Sts2.Core.Nodes;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Ai;

[HarmonyPatch(typeof(CombatRoomHandler), nameof(CombatRoomHandler.HandleAsync))]
internal static class CombatRoomHandlerPatch
{
    private static int _handled;

    private static bool Prefix(Rng random, CancellationToken ct, ref Task __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent") || _handled++ >= int.Parse(CommandLineHelper.GetValue("agent-max-combats") ?? "1"))
            return true;
        __result = CombatBridge.Run(ct);
        return false;
    }
}

internal static class CombatBridge
{
    private sealed record AgentAction(
        int Seq,
        string Type,
        [property: JsonPropertyName("hand_index")] int? HandIndex,
        [property: JsonPropertyName("card_id")] string? CardId,
        [property: JsonPropertyName("target_id")] uint? TargetId,
        [property: JsonPropertyName("simulations")] int? Simulations,
        [property: JsonPropertyName("search_value")] double? SearchValue);

    public static async Task Run(CancellationToken ct)
    {
        while (!CombatManager.Instance.IsInProgress)
            await Task.Delay(50, ct);

        var run = RunManager.Instance.DebugOnlyGetState() ?? throw new InvalidOperationException("run state unavailable");
        var player = LocalContext.GetMe(run) ?? throw new InvalidOperationException("local player unavailable");
        int seq = 0;
        while (CombatManager.Instance.IsInProgress)
        {
            while (CombatManager.Instance.IsInProgress && player.PlayerCombatState?.Phase != PlayerTurnPhase.Play)
                await Task.Delay(50, ct);
            if (!CombatManager.Instance.IsInProgress)
                break;

            var action = await Exchange(run, player, seq++, ct);
            Trace(new { seq = action.Seq, action.Type, hand_index = action.HandIndex, card_id = action.CardId, target_id = action.TargetId, simulations = action.Simulations, search_value = action.SearchValue });
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
            else
            {
                throw new InvalidOperationException($"unknown agent action: {action.Type}");
            }
            await RunManager.Instance.ActionExecutor.FinishedExecutingActions();
        }
        WriteJson(CommandLineHelper.GetValue("bridge-observation")!, new { seq, terminal = true });
        Trace(new { seq, terminal = true });
        if (CommandLineHelper.GetValue("stop-after-agent") == "1")
            NGame.Instance?.GetTree().Quit(0);
    }

    private static async Task<AgentAction> Exchange(RunState run, MegaCrit.Sts2.Core.Entities.Players.Player player, int seq, CancellationToken ct)
    {
        string observationPath = CommandLineHelper.GetValue("bridge-observation") ?? throw new InvalidOperationException("bridge-observation missing");
        string actionPath = CommandLineHelper.GetValue("bridge-action") ?? throw new InvalidOperationException("bridge-action missing");
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
        legal.Add(new { type = "end_turn", hand_index = (int?)null, card_id = (string?)null, target_id = (uint?)null });
        WriteJson(observationPath, new
        {
            seq,
            terminal = false,
            turn = player.PlayerCombatState.TurnNumber,
            run = new { act = run.CurrentActIndex, floor = run.ActFloor },
            player = new
            {
                hp = player.Creature.CurrentHp,
                max_hp = player.Creature.MaxHp,
                block = player.Creature.Block,
                energy = player.PlayerCombatState.Energy,
                powers = player.Creature.Powers.Select(p => new { id = p.Id.ToString(), amount = p.Amount }),
            },
            hand = hand.Select((card, index) => new
            {
                index,
                id = card.Id.ToString(),
                cost = card.EnergyCost.GetWithModifiers(CostModifiers.All),
                upgrade = card.CurrentUpgradeLevel,
                target = card.TargetType.ToString(),
            }),
            draw_pile = player.PlayerCombatState.DrawPile.Cards.Select(card => card.Id.ToString()),
            discard_pile = player.PlayerCombatState.DiscardPile.Cards.Select(card => card.Id.ToString()),
            exhaust_pile = player.PlayerCombatState.ExhaustPile.Cards.Select(card => card.Id.ToString()),
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

        DateTime deadline = DateTime.UtcNow.AddMinutes(2);
        while (DateTime.UtcNow < deadline)
        {
            ct.ThrowIfCancellationRequested();
            if (File.Exists(actionPath))
            {
                try
                {
                    var action = JsonSerializer.Deserialize<AgentAction>(File.ReadAllText(actionPath), new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
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

    private static object Intent(AbstractIntent intent, IReadOnlyList<Creature> targets, Creature owner)
    {
        if (intent is AttackIntent attack)
            return new { type = intent.IntentType.ToString(), damage = attack.GetSingleDamage(targets, owner), repeats = attack.Repeats };
        return new { type = intent.IntentType.ToString(), damage = 0, repeats = 0 };
    }

    private static void WriteJson(string path, object value)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        string temp = path + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(value, new JsonSerializerOptions { WriteIndented = true, PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower }));
        File.Move(temp, path, true);
    }

    private static void Trace(object value)
    {
        string? path = CommandLineHelper.GetValue("bridge-trace");
        if (path is null)
            return;
        File.AppendAllText(path, JsonSerializer.Serialize(value, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower }) + Environment.NewLine);
    }
}
