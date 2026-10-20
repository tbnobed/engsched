"""Automation persistence. Schema is installed by serialized deployment startup."""
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import JSONB
from app import db

JSON = db.JSON().with_variant(JSONB(), 'postgresql')


def now():
    return datetime.now(timezone.utc)


class AutomationRule(db.Model):
    __tablename__ = 'automation_rules'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default='')
    position = db.Column(db.Integer, nullable=False, default=0)
    active = db.Column(db.Boolean, nullable=False, default=True)
    trigger = db.Column(db.String(30), nullable=False)
    custom_triggers = db.Column(JSON, nullable=False, default=list)
    scope = db.Column(db.String(30), nullable=False, default='ticket')
    condition_logic = db.Column(db.String(20), nullable=False, default='all')
    custom_expression = db.Column(db.Text, nullable=False, default='')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now, onupdate=now)
    conditions = db.relationship('AutomationCondition', cascade='all, delete-orphan', order_by='AutomationCondition.number')
    actions = db.relationship('AutomationAction', cascade='all, delete-orphan', order_by='AutomationAction.position')
    __table_args__ = (
        db.CheckConstraint("trigger IN ('created','comment_added','updated','survey_submitted','custom')"),
        db.CheckConstraint("scope = 'ticket'"),
        db.CheckConstraint("condition_logic IN ('all','any','custom')"),
    )


class AutomationCondition(db.Model):
    __tablename__ = 'automation_conditions'
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id', ondelete='CASCADE'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    kind = db.Column(db.String(20), nullable=False, default='regular')
    field_key = db.Column(db.String(100))
    value_type = db.Column(db.String(20), default='current_value')
    operator = db.Column(db.String(40))
    value = db.Column(JSON)
    amount = db.Column(db.Integer)
    unit = db.Column(db.String(20))
    direction = db.Column(db.String(10))
    anchor_field = db.Column(db.String(100))
    public_only = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (db.UniqueConstraint('rule_id', 'number'), db.CheckConstraint('number > 0'),
                      db.CheckConstraint("kind IN ('regular','time_based')"))


class AutomationAction(db.Model):
    __tablename__ = 'automation_actions'
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id', ondelete='CASCADE'), nullable=False)
    position = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(30), nullable=False)
    config = db.Column(JSON, nullable=False, default=dict)


class AutomationRun(db.Model):
    __tablename__ = 'automation_runs'
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id', ondelete='SET NULL'), index=True)
    rule_name = db.Column(db.String(200), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id', ondelete='CASCADE'), nullable=False, index=True)
    trigger_event = db.Column(db.String(30), nullable=False)
    matched = db.Column(db.Boolean, nullable=False, default=False)
    actions_executed = db.Column(JSON, nullable=False, default=list)
    errors = db.Column(JSON, nullable=False, default=list)
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    finished_at = db.Column(db.DateTime(timezone=True))


class AutomationScheduledJob(db.Model):
    __tablename__ = 'automation_scheduled_jobs'
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.Integer, db.ForeignKey('automation_rules.id', ondelete='CASCADE'), nullable=False)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id', ondelete='CASCADE'), nullable=False)
    run_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    status = db.Column(db.String(15), nullable=False, default='pending')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=now)
    __table_args__ = (
        db.CheckConstraint("status IN ('pending','done','cancelled')"),
        db.Index('automation_one_pending', 'rule_id', 'ticket_id', unique=True,
                 postgresql_where=db.text("status = 'pending'"), sqlite_where=db.text("status = 'pending'")),
    )


class AutomationCustomField(db.Model):
    __tablename__ = 'automation_custom_fields'
    key = db.Column(db.String(100), primary_key=True)
    label = db.Column(db.String(150), nullable=False)
    data_type = db.Column(db.String(20), nullable=False)
    choices = db.Column(JSON, nullable=False, default=list)


class AutomationSettings(db.Model):
    __tablename__ = 'automation_settings'
    id = db.Column(db.Integer, primary_key=True)
    timezone = db.Column(db.String(60), nullable=False, default='UTC')
    business_hours = db.Column(JSON, nullable=False, default=dict)
    overflow_alert_at = db.Column(db.DateTime(timezone=True))


class AutomationTicketLink(db.Model):
    __tablename__ = 'automation_ticket_links'
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id', ondelete='CASCADE'), primary_key=True)
    linked_ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id', ondelete='CASCADE'), primary_key=True)
