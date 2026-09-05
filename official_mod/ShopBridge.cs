using System.Text.Json.Serialization;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Rooms;
using MegaCrit.Sts2.Core.AutoSlay.Helpers;
using MegaCrit.Sts2.Core.CardSelection;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.CardRewardAlternatives;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Entities.Merchant;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.Shops;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.TestSupport;

namespace Sts2Ai;

[HarmonyPatch(typeof(ShopRoomHandler), nameof(ShopRoomHandler.HandleAsync))]
internal static class ShopRoomHandlerPatch
{
    private static bool Prefix(Rng random, CancellationToken ct, ref Task __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent"))
            return true;
        __result = ShopBridge.Run(ct);
        return false;
    }
}

internal static class ShopBridge
{
    private const string RoomPath = "/root/Game/RootSceneContainer/Run/RoomContainer/MerchantRoom";

    private sealed record ShopAction(
        int Seq,
        string Type,
        [property: JsonPropertyName("slot_index")] int? SlotIndex,
        [property: JsonPropertyName("index")] int? Index,
        [property: JsonPropertyName("card_index")] int? CardIndex,
        [property: JsonPropertyName("card_id")] string? CardId,
        [property: JsonPropertyName("relic_index")] int? RelicIndex,
        [property: JsonPropertyName("relic_id")] string? RelicId,
        [property: JsonPropertyName("potion_index")] int? PotionIndex,
        [property: JsonPropertyName("potion_id")] string? PotionId,
        [property: JsonPropertyName("item_id")] string? ItemId,
        [property: JsonPropertyName("id")] string? Id,
        [property: JsonPropertyName("decision_source")] string? DecisionSource,
        [property: JsonPropertyName("decision_reason")] string? DecisionReason) : IAgentAction;

    private sealed record ShopSlotRef(NMerchantSlot Slot, int SlotIndex, int ItemIndex, string Id);

    public static async Task Run(CancellationToken ct)
    {
        var root = ((SceneTree)Engine.GetMainLoop()).Root;
        var room = await WaitHelper.ForNode<NMerchantRoom>(root, RoomPath, ct);
        room.OpenInventory();
        await Task.Delay(500, ct);

        var failedSlots = new HashSet<int>();
        int operations = 0;
        int lastSeq = -1;
        try
        {
            var run = RunManager.Instance.DebugOnlyGetState() ?? throw new InvalidOperationException("run state unavailable");
            var player = LocalContext.GetMe(run) ?? throw new InvalidOperationException("local player unavailable");
            while (operations < 64)
            {
                var slots = room.Inventory.GetAllSlots().ToArray();
                int seq = AgentIo.NextSequence();
                lastSeq = seq;
                AgentIo.WriteObservation(Observation(seq, run, player, slots, failedSlots));

                ShopAction action;
                try
                {
                    action = await AgentIo.AwaitAction<ShopAction>(seq, ct);
                }
                catch (TimeoutException)
                {
                    AgentIo.Trace(new { seq, phase = "shop", action = "skip", reason = "agent_timeout", gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = (string?)null, decision_reason = (string?)null });
                    break;
                }

                operations++;
                if (action.Type == "skip")
                {
                    AgentIo.Trace(new { seq, phase = "shop", action = "skip", gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
                    break;
                }

                bool success = await Execute(action, room, slots, player, failedSlots, ct);
                if (!success && !action.SlotIndex.HasValue)
                    break;
            }

            if (operations >= 64)
                AgentIo.Trace(new { seq = lastSeq, phase = "shop", action = "skip", reason = "shop_operation_limit", operations, gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = (string?)null, decision_reason = (string?)null });
        }
        finally
        {
            await CloseAndProceed(room, ct);
        }
    }

    private static object Observation(
        int seq,
        RunState run,
        MegaCrit.Sts2.Core.Entities.Players.Player player,
        IReadOnlyList<NMerchantSlot> slots,
        ISet<int> failedSlots)
    {
        var deck = player.Deck.Cards.Select((card, index) => new
        {
            index,
            id = card.Id.ToString(),
            type = card.Type.ToString(),
            rarity = card.Rarity.ToString(),
            cost = card.EnergyCost.GetWithModifiers(CostModifiers.All),
            upgrade = card.CurrentUpgradeLevel,
            removable = card.IsRemovable,
        }).ToArray();
        var deckIds = deck.Select(card => card.id).ToArray();
        var cards = new List<object>();
        var relics = new List<object>();
        var potions = new List<object>();
        object? removal = null;
        var removeCards = new List<object>();
        var legal = new List<object>();
        int cardIndex = 0;
        int relicIndex = 0;
        int potionIndex = 0;

        for (int slotIndex = 0; slotIndex < slots.Count; slotIndex++)
        {
            var slot = slots[slotIndex];
            if (slot.Entry is MerchantCardEntry cardEntry && cardEntry.CreationResult?.Card is CardModel card)
            {
                bool affordable = cardEntry.IsStocked && cardEntry.EnoughGold;
                string id = card.Id.ToString();
                cards.Add(new
                {
                    index = cardIndex,
                    slot_index = slotIndex,
                    id,
                    type = card.Type.ToString(),
                    rarity = card.Rarity.ToString(),
                    energy_cost = card.EnergyCost.GetWithModifiers(CostModifiers.All),
                    cost = cardEntry.Cost,
                    on_sale = cardEntry.IsOnSale,
                    affordable,
                });
                if (affordable && !failedSlots.Contains(slotIndex))
                    legal.Add(new { type = "buy_card", index = cardIndex, card_index = cardIndex, slot_index = slotIndex, card_id = id });
                cardIndex++;
                continue;
            }

            if (slot.Entry is MerchantRelicEntry relicEntry && relicEntry.Model is RelicModel relic)
            {
                bool affordable = relicEntry.IsStocked && relicEntry.EnoughGold;
                string id = relic.Id.ToString();
                relics.Add(new
                {
                    index = relicIndex,
                    slot_index = slotIndex,
                    id,
                    cost = relicEntry.Cost,
                    affordable,
                });
                if (affordable && !failedSlots.Contains(slotIndex))
                    legal.Add(new { type = "buy_relic", index = relicIndex, relic_index = relicIndex, slot_index = slotIndex, relic_id = id });
                relicIndex++;
                continue;
            }

            if (slot.Entry is MerchantPotionEntry potionEntry && potionEntry.Model is PotionModel potion)
            {
                bool affordable = potionEntry.IsStocked && potionEntry.EnoughGold;
                string id = potion.Id.ToString();
                potions.Add(new
                {
                    index = potionIndex,
                    slot_index = slotIndex,
                    id,
                    cost = potionEntry.Cost,
                    affordable,
                });
                if (affordable && player.PotionSlots.Any(potion => potion is null) && !failedSlots.Contains(slotIndex))
                    legal.Add(new { type = "buy_potion", index = potionIndex, potion_index = potionIndex, slot_index = slotIndex, potion_id = id });
                potionIndex++;
                continue;
            }

            if (slot.Entry is MerchantCardRemovalEntry removalEntry)
            {
                bool affordable = removalEntry.IsStocked && removalEntry.EnoughGold;
                removal = new
                {
                    index = 0,
                    slot_index = slotIndex,
                    id = "remove",
                    cost = removalEntry.Cost,
                    affordable,
                };
                if (affordable && !failedSlots.Contains(slotIndex))
                {
                    foreach (var deckCard in deck.Where(deckCard => deckCard.removable))
                    {
                        removeCards.Add(new
                        {
                            card_index = deckCard.index,
                            card_id = deckCard.id,
                            type = deckCard.type,
                            rarity = deckCard.rarity,
                            slot_index = slotIndex,
                        });
                        legal.Add(new { type = "remove", card_index = deckCard.index, card_id = deckCard.id, slot_index = slotIndex });
                    }
                }
            }
        }

        legal.Add(new { type = "skip" });
        return new
        {
            seq,
            terminal = false,
            phase = "shop",
            run = new
            {
                act = run.CurrentActIndex,
                floor = run.ActFloor,
                seed = run.Rng.StringSeed,
                boss_encounter_id = run.Act.BossEncounter?.Id.ToString(),
                second_boss_encounter_id = run.Act.SecondBossEncounter?.Id.ToString(),
            },
            gold = player.Gold,
            deck = deckIds,
            deck_cards = deck,
            deck_ids = deckIds,
            player = new
            {
                hp = player.Creature.CurrentHp,
                max_hp = player.Creature.MaxHp,
                gold = player.Gold,
                deck = deckIds,
                deck_cards = deck,
            },
            cards,
            relics,
            potions,
            removal,
            remove_cards = removeCards,
            legal_actions = legal,
        };
    }

    private static async Task<bool> Execute(
        ShopAction action,
        NMerchantRoom room,
        IReadOnlyList<NMerchantSlot> slots,
        MegaCrit.Sts2.Core.Entities.Players.Player player,
        ISet<int> failedSlots,
        CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        if (action.Type == "skip")
        {
            AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "skip", gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
            return true;
        }

        var cards = slots
            .Select((slot, index) => (slot, index))
            .Where(item => item.slot.Entry is MerchantCardEntry card && card.CreationResult?.Card is CardModel)
            .Select((item, index) => new ShopSlotRef(item.slot, item.index, index, ((MerchantCardEntry)item.slot.Entry).CreationResult!.Card.Id.ToString()))
            .ToArray();
        var relics = slots
            .Select((slot, index) => (slot, index))
            .Where(item => item.slot.Entry is MerchantRelicEntry relic && relic.Model is RelicModel)
            .Select((item, index) => new ShopSlotRef(item.slot, item.index, index, ((MerchantRelicEntry)item.slot.Entry).Model!.Id.ToString()))
            .ToArray();
        var potions = slots
            .Select((slot, index) => (slot, index))
            .Where(item => item.slot.Entry is MerchantPotionEntry potion && potion.Model is PotionModel)
            .Select((item, index) => new ShopSlotRef(item.slot, item.index, index, ((MerchantPotionEntry)item.slot.Entry).Model!.Id.ToString()))
            .ToArray();

        if (action.Type == "buy_card")
        {
            var selected = Find(cards, action.SlotIndex, action.CardIndex ?? action.Index, action.CardId ?? action.ItemId ?? action.Id);
            if (selected is not null && selected.Slot.Entry is MerchantCardEntry entry && entry.IsStocked && entry.EnoughGold)
            {
                bool purchased = await entry.OnTryPurchaseWrapper(room.Inventory.Inventory);
                AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "buy_card", card_id = selected.Id, slot_index = selected.SlotIndex, purchased, gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
                if (purchased)
                    return true;
            }
            if (action.SlotIndex is int failedSlot)
                failedSlots.Add(failedSlot);
            AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "skip", reason = "invalid_card_action", gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
            return false;
        }

        if (action.Type == "buy_relic")
        {
            var selected = Find(relics, action.SlotIndex, action.RelicIndex ?? action.Index, action.RelicId ?? action.ItemId ?? action.Id);
            if (selected is not null && selected.Slot.Entry is MerchantRelicEntry entry && entry.IsStocked && entry.EnoughGold)
            {
                bool purchased = await entry.OnTryPurchaseWrapper(room.Inventory.Inventory);
                AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "buy_relic", relic_id = selected.Id, slot_index = selected.SlotIndex, purchased, gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
                if (purchased)
                    return true;
            }
            if (action.SlotIndex is int failedSlot)
                failedSlots.Add(failedSlot);
            AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "skip", reason = "invalid_relic_action", gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
            return false;
        }

        if (action.Type == "buy_potion")
        {
            var selected = Find(potions, action.SlotIndex, action.PotionIndex ?? action.Index, action.PotionId ?? action.ItemId ?? action.Id);
            if (selected is not null && selected.Slot.Entry is MerchantPotionEntry entry && entry.IsStocked && entry.EnoughGold && player.PotionSlots.Any(potion => potion is null))
            {
                bool purchased = await entry.OnTryPurchaseWrapper(room.Inventory.Inventory);
                AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "buy_potion", potion_id = selected.Id, slot_index = selected.SlotIndex, purchased, gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
                if (purchased)
                    return true;
            }
            if (action.SlotIndex is int failedSlot)
                failedSlots.Add(failedSlot);
            AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "skip", reason = player.PotionSlots.Any(potion => potion is null) ? "invalid_potion_action" : "potion_slots_full", gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
            return false;
        }

        if (action.Type == "remove")
        {
            var removal = slots
                .Select((slot, index) => (slot, index))
                .FirstOrDefault(item => item.slot.Entry is MerchantCardRemovalEntry entry &&
                    entry.IsStocked && entry.EnoughGold &&
                    (!action.SlotIndex.HasValue || action.SlotIndex.Value == item.index));
            int cardIndex = action.CardIndex ?? action.Index ?? -1;
            var deck = player.Deck.Cards;
            var card = cardIndex >= 0 && cardIndex < deck.Count ? deck[cardIndex] : null;
            if (removal.slot is not null && card is not null && card.IsRemovable &&
                action.CardId == card.Id.ToString() &&
                removal.slot.Entry is MerchantCardRemovalEntry removalEntry)
            {
                using var selector = CardSelectCmd.PushSelector(new ExactCardSelector(card));
                bool purchased = await removalEntry.OnTryPurchaseWrapper(room.Inventory.Inventory);
                AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "remove", card_index = cardIndex, card_id = card.Id.ToString(), purchased, gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
                if (purchased)
                    return true;
            }
            if (action.SlotIndex is int failedSlot)
                failedSlots.Add(failedSlot);
            AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "skip", reason = "invalid_remove_action", gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
            return false;
        }

        // Unknown shop actions are always a no-op; the inventory is still closed below.
        AgentIo.Trace(new { seq = action.Seq, phase = "shop", action = "skip", reason = "unsupported_shop_action", requested = action.Type, gold = player.Gold, deck = player.Deck.Cards.Select(card => card.Id.ToString()), decision_source = action.DecisionSource, decision_reason = action.DecisionReason });
        return false;
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

    private static ShopSlotRef? Find(
        IReadOnlyList<ShopSlotRef> candidates,
        int? slotIndex,
        int? itemIndex,
        string? id)
    {
        if (string.IsNullOrEmpty(id))
            return null;
        return candidates.FirstOrDefault(candidate =>
            candidate.Id == id &&
            (!slotIndex.HasValue || candidate.SlotIndex == slotIndex.Value) &&
            (!itemIndex.HasValue || candidate.ItemIndex == itemIndex.Value));
    }

    private static async Task CloseAndProceed(NMerchantRoom room, CancellationToken ct)
    {
        var back = UiHelper.FindFirst<NBackButton>(room);
        if (back is not null)
        {
            await UiHelper.Click(back);
            await Task.Delay(300, ct);
        }
        await UiHelper.Click(room.ProceedButton);
    }
}
