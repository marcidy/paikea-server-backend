"""
Serializers use Marshmallow to translate database representations to json and
vice versa
"""
import paikea.models as md
from .extensions import ma


class StatusSchema(ma.SQLAlchemySchema):
    class Meta:
        model = md.RBMessageStatus

    status = ma.auto_field()


class RockBlockMessageSchema(ma.SQLAlchemySchema):
    class Meta:
        model = md.RockBlockMessage
        include_fk = True

    id = ma.auto_field()
    imei = ma.auto_field()
    data = ma.auto_field()
    status = ma.Nested(StatusSchema)
    serial = ma.auto_field()
    transmit_time = ma.auto_field()
    iridium_latitude = ma.auto_field()
    iridium_longitude = ma.auto_field()
    iridium_session_status = ma.auto_field()


class RBModemSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.RockBlockModem
        include_fk = True


class RockStarSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.RockStar
        include_fk = True


class SQSEndpointSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.SQS_Endpoint
        include_fk = True


class BuoySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.Buoy
        include_fk = True


class PK001Schema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.PK001
        include_fk = True


class PK004Schema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.PK004
        include_fk = True


class MessageParsingErrorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.MessageParsingError
        include_fk = True


class RockCorePushAPI(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.RockCorePushAPI
        include_fk = True
        load_instance = True


class HandsetSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.Handset
        include_fk = True


class EndpointRouterSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = md.EndpointRoute
        include_fk = True
