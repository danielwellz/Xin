"""${message}"""

revision = ${repr(revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """Apply upgrade migrations."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Revert upgrade migrations."""
    ${downgrades if downgrades else "pass"}
