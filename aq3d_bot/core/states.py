from enum import Enum


class BotState(Enum):
    """All possible states for the bot state machine."""
    IDLE = "Idle"
    SEARCHING = "Searching"
    ATTACKING = "Attacking"
    LOOTING = "Looting"
    MOVING = "Moving"
    DEAD = "Dead"
    REVIVING = "Reviving"
    RUNNING_BACK = "Running Back"
    AFK = "AFK"
