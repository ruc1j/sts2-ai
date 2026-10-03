#!/usr/bin/env python3
"""Experiment harness: the arm with the generation sets pinned to the control shapes (`e808bdf`).

The pool-fidelity fix (`77120b2`) changes what a rollout can imagine being generated, which confounds
mechanism-only attribution in real runs. Pinning both sets to the control shapes leaves the mechanism
implementations as the only difference, so a divergence under this harness is mechanism-only. This is a
measurement harness, not a policy change - the adopted code stays as it is.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import combat
import official_agent

CONTROL_STOKE_GENERATION = (
    'Aggression', 'Anger', 'Armaments', 'Ashen Strike', 'Barricade', 'Battle Trance',
    'Believe in You', 'Blood Wall', 'Bloodletting', 'Bludgeon', 'Body Slam', 'Bolas', 'Brand',
    'Break', 'Breakthrough', 'Bully', 'Burning Pact', 'Byrd Swoop', 'Cascade', 'Cinder',
    'Colossus', 'Conflagration', 'Crimson Mantle', 'Cruelty', 'Dark Embrace', 'Demon Form',
    'Dismantle', 'Dominate', 'Dramatic Entrance', 'Drum of Battle', 'Enlightenment',
    'Equilibrium', 'Evil Eye', 'Expect a Fight', 'Exterminate', 'Fasten', 'Feed',
    'Feel No Pain', 'Fiend Fire', 'Fight Me', 'Finesse', 'Fisticuffs', 'Flame Barrier',
    'Flash of Steel', 'Forgotten Ritual', 'Giant Rock', 'Havoc', 'Headbutt', 'Hellraiser',
    'Hemokinesis', 'Howl From Beyond', 'Impatience', 'Impervious', 'Infernal Blade', 'Inferno',
    'Inflame', 'Iron Wave', 'Juggernaut', 'Juggling', 'Lift', 'Mad Science', 'Mangle',
    'Master of Strategy', 'Maul', 'Metamorphosis', 'Mind Blast', 'Molten Fist', "Neow's Fury",
    'Not Yet', 'Offering', 'Pacts End', 'Peck', 'Perfected Strike', 'Pillage', 'Pommel Strike',
    'Primal Force', 'Production', 'Purity', 'Pyre', 'Rage', 'Rampage', 'Relax', 'Rupture',
    'Salvo', 'Second Wind', 'Setup Strike', 'Shrug It Off', 'Spite', 'Squash', 'Stampede',
    'Stoke', 'Stomp', 'Stone Armor', 'Sword Boomerang', 'Taunt', 'Tear Asunder', 'Thrash',
    'Thrumming Hatchet', 'Thunderclap', 'Toric Toughness', 'Tremble', 'True Grit',
    'Twin Strike', 'Ultimate Defend', 'Ultimate Strike', 'Unmovable', 'Unrelenting',
    'Uppercut', 'Vicious', 'Volley'
)

CONTROL_INFERNAL_BLADE_ATTACKS = (
    'Anger', 'Ashen Strike', 'Bludgeon', 'Body Slam', 'Bolas', 'Break', 'Breakthrough',
    'Bully', 'Byrd Swoop', 'Cinder', 'Conflagration', 'Dismantle', 'Dramatic Entrance',
    'Exterminate', 'Feed', 'Fiend Fire', 'Fight Me', 'Fisticuffs', 'Flash of Steel',
    'Giant Rock', 'Headbutt', 'Hemokinesis', 'Howl From Beyond', 'Iron Wave', 'Mangle', 'Maul',
    'Mind Blast', 'Molten Fist', "Neow's Fury", 'Pacts End', 'Peck', 'Perfected Strike',
    'Pillage', 'Pommel Strike', 'Rampage', 'Salvo', 'Setup Strike', 'Spite', 'Squash', 'Stomp',
    'Sword Boomerang', 'Tear Asunder', 'Thrash', 'Thrumming Hatchet', 'Thunderclap',
    'Twin Strike', 'Ultimate Strike', 'Unrelenting', 'Uppercut', 'Volley', 'Whirlwind'
)

combat.STOKE_GENERATION = CONTROL_STOKE_GENERATION
combat.INFERNAL_BLADE_ATTACKS = CONTROL_INFERNAL_BLADE_ATTACKS

if __name__ == "__main__":
    official_agent.main()
