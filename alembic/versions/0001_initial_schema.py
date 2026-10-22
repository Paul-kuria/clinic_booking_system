"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-10-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Doctors table
    op.create_table(
        'doctors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('specialty', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_doctors_id'), 'doctors', ['id'], unique=False)
    op.create_index(op.f('ix_doctors_email'), 'doctors', ['email'], unique=True)

    # 2. Doctor Schedules table
    op.create_table(
        'doctor_schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Time(), nullable=False),
        sa.Column('end_time', sa.Time(), nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_doctor_schedules_id'), 'doctor_schedules', ['id'], unique=False)
    op.create_index(op.f('ix_doctor_schedules_doctor_id'), 'doctor_schedules', ['doctor_id'], unique=False)

    # 3. Patients table
    op.create_table(
        'patients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('phone', sa.String(length=30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_patients_id'), 'patients', ['id'], unique=False)
    op.create_index(op.f('ix_patients_email'), 'patients', ['email'], unique=True)

    # 4. Appointments table
    op.create_table(
        'appointments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doctor_id', sa.Integer(), nullable=False),
        sa.Column('patient_id', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            'status',
            sa.Enum('BOOKED', 'CANCELLED', name='appointment_status'),
            nullable=False,
        ),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_appointments_id'), 'appointments', ['id'], unique=False)
    op.create_index(op.f('ix_appointments_doctor_id'), 'appointments', ['doctor_id'], unique=False)
    op.create_index(op.f('ix_appointments_patient_id'), 'appointments', ['patient_id'], unique=False)
    op.create_index(op.f('ix_appointments_start_time'), 'appointments', ['start_time'], unique=False)
    op.create_index(op.f('ix_appointments_status'), 'appointments', ['status'], unique=False)

    # 5. PostgreSQL Partial Unique Indexes for Double-Booking Prevention
    op.create_index(
        'uq_doctor_active_slot',
        'appointments',
        ['doctor_id', 'start_time'],
        unique=True,
        postgresql_where=sa.text("status = 'BOOKED'"),
    )
    op.create_index(
        'uq_patient_active_slot',
        'appointments',
        ['patient_id', 'start_time'],
        unique=True,
        postgresql_where=sa.text("status = 'BOOKED'"),
    )


def downgrade() -> None:
    op.drop_index('uq_patient_active_slot', table_name='appointments')
    op.drop_index('uq_doctor_active_slot', table_name='appointments')
    op.drop_index(op.f('ix_appointments_status'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_start_time'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_patient_id'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_doctor_id'), table_name='appointments')
    op.drop_index(op.f('ix_appointments_id'), table_name='appointments')
    op.drop_table('appointments')

    op.drop_index(op.f('ix_patients_email'), table_name='patients')
    op.drop_index(op.f('ix_patients_id'), table_name='patients')
    op.drop_table('patients')

    op.drop_index(op.f('ix_doctor_schedules_doctor_id'), table_name='doctor_schedules')
    op.drop_index(op.f('ix_doctor_schedules_id'), table_name='doctor_schedules')
    op.drop_table('doctor_schedules')

    op.drop_index(op.f('ix_doctors_email'), table_name='doctors')
    op.drop_index(op.f('ix_doctors_id'), table_name='doctors')
    op.drop_table('doctors')

    sa.Enum(name='appointment_status').drop(op.get_bind(), checkfirst=False)
