using HarmonyLib;
using MegaCrit.Sts2.Core.AutoSlay.Handlers.Screens;
using MegaCrit.Sts2.Core.Context;
using MegaCrit.Sts2.Core.GameActions;
using MegaCrit.Sts2.Core.Helpers;
using MegaCrit.Sts2.Core.Map;
using MegaCrit.Sts2.Core.Multiplayer.Game;
using MegaCrit.Sts2.Core.Random;
using MegaCrit.Sts2.Core.Runs;

namespace Sts2Ai;

[HarmonyPatch(typeof(MapScreenHandler), nameof(MapScreenHandler.HandleAsync))]
internal static class MapScreenHandlerPatch
{
    private static bool Prefix(Rng random, CancellationToken ct, ref Task __result)
    {
        if (!CommandLineHelper.HasArg("sts2ai-agent"))
            return true;
        __result = MapBridge.Run(ct);
        return false;
    }
}

internal static class MapBridge
{
    private static bool _wroteMap;

    private sealed record MapAction(
        int Seq,
        string Type,
        int Col,
        int Row) : IAgentAction;

    public static async Task Run(CancellationToken ct)
    {
        var run = RunManager.Instance.DebugOnlyGetState() ?? throw new InvalidOperationException("run state unavailable");
        var player = LocalContext.GetMe(run) ?? throw new InvalidOperationException("local player unavailable");
        string requestedSeed = CommandLineHelper.GetValue("seed") ?? run.Rng.StringSeed;
        if (run.Rng.StringSeed != requestedSeed)
            throw new InvalidOperationException($"run seed changed: {run.Rng.StringSeed} != {requestedSeed}");
        var legal = LegalPoints(run).ToArray();
        if (legal.Length == 0)
            throw new InvalidOperationException("map has no legal destination");

        int seq = AgentIo.NextSequence();
        var allPoints = new[] { run.Map.StartingMapPoint }
            .Concat(run.Map.GetAllMapPoints())
            .Append(run.Map.BossMapPoint)
            .DistinctBy(point => (point.coord.col, point.coord.row))
            .ToArray();
        var map = new
        {
            game_version = "v0.107.1",
            seed = run.Rng.StringSeed,
            act = run.Act.Id.ToString(),
            rows = allPoints.Max(point => point.coord.row) + 1,
            columns = run.Map.GetColumnCount(),
            points = allPoints.Select(point => new
            {
                id = $"{point.coord.col}:{point.coord.row}",
                col = point.coord.col,
                row = point.coord.row,
                type = point.PointType.ToString(),
                parents = point.parents.Select(parent => new { col = parent.coord.col, row = parent.coord.row }),
                children = point.Children.Select(child => new { col = child.coord.col, row = child.coord.row }),
            }).ToArray(),
        };
        string? mapPath = CommandLineHelper.GetValue("bridge-map");
        if (!_wroteMap && mapPath is not null)
        {
            AgentIo.WriteJson(mapPath, map);
            _wroteMap = true;
        }
        AgentIo.WriteObservation(new
        {
            seq,
            terminal = false,
            phase = "map",
            run = new
            {
                act = run.CurrentActIndex,
                floor = run.ActFloor,
                seed = run.Rng.StringSeed,
                current = run.CurrentMapCoord is MapCoord coord ? new { col = coord.col, row = coord.row } : null,
                visited = run.VisitedMapCoords.Select(point => new { col = point.col, row = point.row }),
            },
            player = new { hp = player.Creature.CurrentHp, max_hp = player.Creature.MaxHp },
            map,
            legal_actions = legal.Select(point => new { type = "map", col = point.coord.col, row = point.coord.row, point_type = point.PointType.ToString() }),
        });

        var action = await AgentIo.AwaitAction<MapAction>(seq, ct);
        var selected = legal.FirstOrDefault(point => point.coord.col == action.Col && point.coord.row == action.Row);
        if (action.Type != "map" || selected is null)
            throw new InvalidOperationException($"illegal map action: {action.Col},{action.Row}");
        AgentIo.Trace(new { seq, phase = "map", seed = run.Rng.StringSeed, action.Type, col = action.Col, row = action.Row, point_type = selected.PointType.ToString() });

        var entered = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        void OnEntered() => entered.TrySetResult();
        RunManager.Instance.RoomEntered += OnEntered;
        try
        {
            var vote = new MapVote
            {
                coord = selected.coord,
                mapGenerationCount = RunManager.Instance.MapSelectionSynchronizer.MapGenerationCount,
            };
            RunManager.Instance.ActionQueueSynchronizer.RequestEnqueue(
                new VoteForMapCoordAction(player, new MapLocation(run.CurrentMapCoord, run.CurrentActIndex), vote));
            await entered.Task.WaitAsync(TimeSpan.FromMinutes(2), ct);
        }
        finally
        {
            RunManager.Instance.RoomEntered -= OnEntered;
        }
    }

    private static IEnumerable<MapPoint> LegalPoints(RunState run)
    {
        if (run.VisitedMapCoords.Count == 0)
            return [run.Map.StartingMapPoint];
        var current = run.CurrentMapPoint ?? throw new InvalidOperationException("current map point unavailable");
        if (run.Map.SecondBossMapPoint is not null && current.coord == run.Map.BossMapPoint.coord)
            return [run.Map.SecondBossMapPoint];
        if (current.coord.row == run.Map.GetRowCount() - 1)
            return [run.Map.BossMapPoint];
        return MapTravel.GetTravelablePointsFrom(run, current);
    }
}
