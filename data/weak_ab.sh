#!/bin/zsh
# A/B panel for the combined Weak x Vulnerable rounding (commit d3a9608).
#
# arm = main HEAD.  control = .wt-ctrl-weak at dd2f0f4, so the policy code differs by that one commit.
# Same mod binary, checked by md5.
#
# What the fix changes: the game multiplies ModifyDamageMultiplicative factors together and rounds once,
# so an upgraded Strike (9) played by a Weak player onto a Vulnerable boss deals 9 * 0.75 * 1.5 = 10.125
# -> 10, where the chained model scored 9 * 3 // 4 = 6 then 6 * 150 // 100 = 9.  Offline replay: attack
# agreement 97.48% -> 97.81% over 44,883 plays (the Weak+Vulnerable group went 263/170 to 407/26), and
# 267 recorded decisions changed across 27 seeds.
#
# Seeds: the mechanism only fires while the player holds Weak, which in real runs comes from boss debuffs.
# Every Weak-heavy seed in the corpus was already measured in an earlier panel, so this panel deliberately
# re-measures three of them (player Weak observations 54 / 54 / 48, QUEEN-fight observations 1355 / 207 /
# 48) and is labelled as mechanism-targeted rather than a new seed sample.
set -u
repo=/Users/mao/workspace/sts2-ai
ctrl=$repo/.wt-ctrl-weak
if pgrep -f "SlayTheSpire2" > /dev/null; then
  print -- "refusing: a game run is already in flight"
  exit 1
fi
if [ -n "$(git -C $repo status --short -- official_agent.py combat.py)" ]; then
  print -- "refusing: policy code differs from HEAD (contamination risk)"
  exit 1
fi
if [ ! -f $ctrl/official_mod/bin/Release/net9.0/Sts2Ai.dll ]; then
  print -- "refusing: the control worktree has no mod binary"
  exit 1
fi
if [ "$(md5 -q $repo/official_mod/bin/Release/net9.0/Sts2Ai.dll)" != "$(md5 -q $ctrl/official_mod/bin/Release/net9.0/Sts2Ai.dll)" ]; then
  print -- "refusing: arm and control would run different mod binaries"
  exit 1
fi
seeds=(N8CQ4ZKP2W P3V8N5K2RX T5R8K2N9QP)
REPO=$ctrl /Users/mao/.sts2/scripts/sweep2.sh weak_ctrl_b1 "${seeds[@]}"
REPO=$repo /Users/mao/.sts2/scripts/sweep2.sh weak_arm_b1 "${seeds[@]}"
for seed in "${seeds[@]}"; do
  python3 data/compare_panel.py weak_arm_b1 weak_ctrl_b1 "$repo" "$ctrl" "$seed"
done
print -- "WEAK AB DONE"
