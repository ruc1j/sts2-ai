using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Rooms;
using MegaCrit.Sts2.Core.AutoSlay.Helpers;
using MegaCrit.Sts2.Core.Commands;
using MegaCrit.Sts2.Core.Entities.CardRewardAlternatives;
using MegaCrit.Sts2.Core.Entities.Cards;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Models;
using MegaCrit.Sts2.Core.Nodes.CommonUi;
using MegaCrit.Sts2.Core.Nodes.RestSite;
using MegaCrit.Sts2.Core.Nodes.Rooms;
using MegaCrit.Sts2.Core.Nodes.Screens.Overlays;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;
using MegaCrit.Sts2.Core.TestSupport;

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
        using var selector = action.OptionId == "SMITH"
            ? CardSelectCmd.PushSelector(new SmithCardSelector(player.Deck.Cards.Select(card => card.Id.ToString()), run.CurrentActIndex, run.ActFloor))
            : null;
        await UiHelper.Click(buttons[action.Index]);
        var proceed = room.ProceedButton;
        await WaitHelper.Until(() => proceed.IsEnabled || NOverlayStack.Instance?.ScreenCount > 0, ct, TimeSpan.FromSeconds(10), "rest option did not respond");
        if (NOverlayStack.Instance?.ScreenCount == 0)
            await UiHelper.Click(proceed);
    }

    private sealed class SmithCardSelector : ICardSelector
    {
        private static readonly IReadOnlyDictionary<string, int> StrongBlock = new Dictionary<string, int>
        {
            ["CARD.IMPERVIOUS"] = 100,
            ["CARD.SHRUG_IT_OFF"] = 95,
            ["CARD.FLAME_BARRIER"] = 95,
            ["CARD.BLOOD_WALL"] = 90,
            ["CARD.STONE_ARMOR"] = 90,
            ["CARD.EQUILIBRIUM"] = 90,
            ["CARD.ULTIMATE_DEFEND"] = 90,
            ["CARD.TAUNT"] = 85,
        };

        private readonly HashSet<string> _deck;
        private readonly bool _nearBoss;

        public SmithCardSelector(IEnumerable<string> deck, int act, int floor)
        {
            _deck = deck.ToHashSet();
            var bossFloor = act switch
            {
                0 => 17,
                1 => 16,
                2 => 15,
                _ => 15,
            };
            _nearBoss = floor >= bossFloor - 3;
        }

        public Task<IEnumerable<CardModel>> GetSelectedCards(IEnumerable<CardModel> options, int minSelect, int maxSelect)
        {
            var selected = options.MaxBy(Score);
            return Task.FromResult<IEnumerable<CardModel>>(selected is null ? Array.Empty<CardModel>() : [selected]);
        }

        public CardRewardSelection GetSelectedCardReward(IReadOnlyList<CardCreationResult> options, IReadOnlyList<CardRewardAlternative> alternatives) => default;

        private int Score(CardModel card)
        {
            var id = card.Id.ToString();
            if (_nearBoss && StrongBlock.TryGetValue(id, out var blockScore))
                return 1000 + blockScore;
            if (_deck.Contains("CARD.PERFECTED_STRIKE") && id is "CARD.PERFECTED_STRIKE" or "CARD.HELLRAISER")
                return 700;
            if (_deck.Contains("CARD.RUPTURE") && id is "CARD.RUPTURE" or "CARD.TEAR_ASUNDER" or "CARD.HEMOKINESIS" or "CARD.BLOODLETTING")
                return 680;
            if (_deck.Contains("CARD.CORRUPTION") && id is "CARD.CORRUPTION" or "CARD.FEEL_NO_PAIN" or "CARD.DARK_EMBRACE")
                return 660;
            if (id is "CARD.INFLAME" or "CARD.PRIMAL_FORCE" or "CARD.DOMINATE")
                return 640;
            return id switch
            {
                "CARD.BATTLE_TRANCE" or "CARD.POMMEL_STRIKE" => 600,
                "CARD.BASH" => 550,
                "CARD.IRON_WAVE" or "CARD.SECOND_WIND" or "CARD.TRUE_GRIT" => _nearBoss ? 520 : 500,
                "CARD.STRIKE_IRONCLAD" => 100,
                _ => 300,
            };
        }
    }
}
