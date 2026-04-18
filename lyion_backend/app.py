# =============================================================================
# app.py — Flask application factory for the Ly-ion backend.
# =============================================================================

from flask import Flask
from flask_jwt_extended import JWTManager
from models import db
from config import get_config


def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class or get_config())

    # Initialise extensions
    db.init_app(app)
    JWTManager(app)

    # Register blueprints
    from routes.auth   import auth_bp
    from routes.rental import rental_bp
    from routes.slots  import slots_bp
    from routes.admin  import admin_bp
    from routes.sync   import sync_bp

    app.register_blueprint(auth_bp,   url_prefix="/api/auth")
    app.register_blueprint(rental_bp, url_prefix="/api")
    app.register_blueprint(slots_bp,  url_prefix="/api")
    app.register_blueprint(admin_bp,  url_prefix="/api/admin")
    app.register_blueprint(sync_bp,   url_prefix="/api/sync")

    # Create tables on first run
    with app.app_context():
        db.create_all()
        _seed_default_station(app)

    return app


def _seed_default_station(app):
    """Create the default station if it doesn't exist yet."""
    from models import Station, Slot
    import os
    station_id = os.getenv("STATION_ID", "station-001")
    if not Station.query.get(station_id):
        station = Station(id=station_id, location_name="Main Campus Library")
        db.session.add(station)
        # Create 24 slot records for this station
        for slot_id in range(1, 25):
            slot = Slot(id=slot_id, station_id=station_id)
            db.session.add(slot)
        db.session.commit()
        app.logger.info("Default station '%s' seeded with 24 slots", station_id)


if __name__ == "__main__":
    application = create_app()
    application.run(host="0.0.0.0", port=5000, debug=False)
