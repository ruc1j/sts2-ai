using System.Text.Json.Serialization;
using Godot;
using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Screens;
using MegaCrit.Sts2.Core.AutoSlay.Helpers;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.Entities.CardRewardAlternatives;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Nodes.Cards.Holders;
using MegaCrit.Sts2.Core.Nodes.GodotExtensions;
using MegaCrit.Sts2.Core.Nodes.Screens.CardSelection;
using MegaCrit.Sts2.Core.Nodes.Rewards;
using MegaCrit.Sts2.Core.Nodes.Screens;
using MegaCrit.Sts2.Core.Rewards;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Ai;

[HarmonyPatch(typeof(NCardRewardSelectionScreen), nameof(NCardRewardSelectionScreen.ShowScreen))]
internal static class CardRewardSelectionScreenPatch
{
    private static void Postfix(
        IReadOnlyList<CardCreationResult> options,
        IReadOnlyList<CardRewardAlternative> extraOptions,
        NCardRewardSelectionScreen? __result) => RewardBridge.Capture(__result, options, extraOptions);
}

[HarmonyPatch(typeof(CardRewardScreenHandler), nameof(CardRewardScreenHandler.HandleAsync))]
internal static class CardRewardScreenHandlerPatch
{
    private static bool Prefix(CancellationToken ct, ref Task __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent"))
            return true;
        __result = RewardBridge.Run(ct);
        return false;
    }
}

internal static class RewardBridge
{
    private sealed record RewardAction(
        int Seq,
        string Type,
        [property: JsonPropertyName("card_index")] int? CardIndex,
        [property: JsonPropertyName("card_id")] string? CardId,
        [property: JsonPropertyName("option_index")] int? OptionIndex,
        [property: JsonPropertyName("option_id")] string? OptionId) : IAgentAction;

    private static NCardRewardSelectionScreen? _screen;
    private static IReadOnlyList<CardCreationResult>? _cards;
    private static IReadOnlyList<CardRewardAlternative>? _alternatives;

    public static void Capture(
        NCardRewardSelectionScreen? screen,
        IReadOnlyList<CardCreationResult> cards,
        IReadOnlyList<CardRewardAlternative> alternatives)
    {
        _screen = screen;
        _cards = cards;
        _alternatives = alternatives;
    }

    public static async Task Run(CancellationToken ct)
    {
        var screen = _screen ?? throw new InvalidOperationException("card reward screen unavailable");
        var cards = _cards ?? throw new InvalidOperationException("card rewards unavailable");
        var alternatives = _alternatives ?? [];
        var run = RunManager.Instance.DebugOnlyGetState() ?? throw new InvalidOperationException("run state unavailable");
        var player = LocalContext.GetMe(run) ?? throw new InvalidOperationException("local player unavailable");
        int seq = AgentIo.NextSequence();
        AgentIo.WriteObservation(new
        {
            seq,
            terminal = false,
            phase = "card_reward",
            run = new { act = run.CurrentActIndex, floor = run.ActFloor },
            player = new
            {
                hp = player.Creature.CurrentHp,
                max_hp = player.Creature.MaxHp,
                gold = player.Gold,
                deck = player.Deck.Cards.Select(card => new
                {
                    id = card.Id.ToString(),
                    upgrade = card.CurrentUpgradeLevel,
                    cost = card.EnergyCost.GetWithModifiers(CostModifiers.All),
                }),
            },
            cards = cards.Select((result, index) => new
            {
                index,
                id = result.Card.Id.ToString(),
                type = result.Card.Type.ToString(),
                rarity = result.Card.Rarity.ToString(),
                cost = result.Card.EnergyCost.GetWithModifiers(CostModifiers.All),
                upgrade = result.Card.CurrentUpgradeLevel,
                pool = result.Card.Pool.Id.ToString(),
            }),
            legal_actions = cards.Select((result, index) => (object)new
                {
                    type = "card_reward",
                    card_index = index,
                    card_id = result.Card.Id.ToString(),
                    option_index = (int?)null,
                    option_id = (string?)null,
                })
                .Concat(alternatives.Select((option, index) => (object)new
                {
                    type = "card_reward_alternative",
                    card_index = (int?)null,
                    card_id = (string?)null,
                    option_index = index,
                    option_id = option.OptionId,
                })),
        });

        var action = await AgentIo.AwaitAction<RewardAction>(seq, ct);
        bool skippedSet = false;
        if (action.Type == "card_reward" && action.CardIndex is int cardIndex &&
            cardIndex >= 0 && cardIndex < cards.Count && action.CardId == cards[cardIndex].Card.Id.ToString())
        {
            var holder = screen.GetCardHolder(cards[cardIndex].Card);
            AgentIo.Trace(new { seq, phase = "card_reward", action.Type, card_index = cardIndex, card_id = action.CardId, cards = cards.Select(result => result.Card.Id.ToString()) });
            holder.EmitSignal(NCardHolder.SignalName.Pressed, holder);
        }
        else if (action.Type == "card_reward_alternative" && action.OptionIndex is int optionIndex &&
            optionIndex >= 0 && optionIndex < alternatives.Count && action.OptionId == alternatives[optionIndex].OptionId)
        {
            var buttons = screen.GetNode<Control>("UI/RewardAlternatives").GetChildren().OfType<NCardRewardAlternativeButton>().ToArray();
            if (optionIndex >= buttons.Length)
                throw new InvalidOperationException($"card reward option button unavailable: {optionIndex}");
            AgentIo.Trace(new { seq, phase = "card_reward", action.Type, option_index = optionIndex, option_id = action.OptionId, cards = cards.Select(result => result.Card.Id.ToString()) });
            buttons[optionIndex].EmitSignal(NClickableControl.SignalName.Released, buttons[optionIndex]);
            skippedSet = action.OptionId == "Skip";
        }
        else
        {
            throw new InvalidOperationException($"illegal card reward action: {action.Type}");
        }
        DateTime deadline = DateTime.UtcNow.AddSeconds(10);
        while (GodotObject.IsInstanceValid(screen) && screen.IsVisibleInTree() && DateTime.UtcNow < deadline)
            await Task.Delay(25, ct);
        if (GodotObject.IsInstanceValid(screen) && screen.IsVisibleInTree())
            throw new TimeoutException("card reward screen did not close");
        if (skippedSet)
        {
            RunManager.Instance.RewardsSetSynchronizer.SkipLocalRewardsSet();
            await Task.Delay(50, ct);
            var rewardsScreen = AutoSlayer.GetCurrentScreen<NRewardsScreen>();
            var button = UiHelper.FindAll<NRewardButton>(rewardsScreen).FirstOrDefault(item => item.Reward is CardReward);
            if (button is not null)
                rewardsScreen.RewardCollectedFrom(button);
        }
        _screen = null;
        _cards = null;
        _alternatives = null;
        if (CommandLineHelper.GetValue("stop-after-reward") == "1")
        {
            int terminalSeq = AgentIo.NextSequence();
            AgentIo.WriteObservation(new { seq = terminalSeq, terminal = true });
            AgentIo.Trace(new { seq = terminalSeq, terminal = true });
            MegaCrit.Sts2.Core.Nodes.NGame.Instance?.GetTree().Quit(0);
        }
    }
}
