"""Flask application entry point for the College Notice Assistant API."""

import logging
import os

from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from config import Config
from routes.health import health_bp
from routes.summarize import summarize_bp
from services.file_validation import MAX_FILE_SIZE


def create_app() -> Flask:
    """Create and configure the Flask application."""
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    flask_app = Flask(__name__)
    flask_app.config.from_object(Config)
    flask_app.logger.setLevel(logging.INFO)
    frontend_url = flask_app.config['FRONTEND_URL']
    if flask_app.config['IS_PRODUCTION'] and not frontend_url:
        raise RuntimeError('FRONTEND_URL must be set for a production deployment.')
    # Flask counts multipart boundaries and form headers toward this limit.  Leave
    # room for that small overhead while validate_upload enforces the actual
    # document limit of 10 MiB.
    flask_app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE + (1024 * 1024)

    CORS(
        flask_app,
        resources={r'/api/*': {'origins': frontend_url}},
        methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    )

    flask_app.register_blueprint(health_bp)
    flask_app.register_blueprint(summarize_bp)
    register_error_handlers(flask_app)
    return flask_app


def register_error_handlers(flask_app: Flask) -> None:
    """Register consistent JSON responses for API errors."""

    @flask_app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify({
            'success': False,
            'message': error.description,
            'status': 'error',
        }), error.code

    @flask_app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        flask_app.logger.exception('Unhandled application error: %s', error)
        return jsonify({
            'success': False,
            'message': 'An unexpected server error occurred.',
            'status': 'error',
        }), 500


# Vercel and WSGI servers use this exported application instance.
app = create_app()


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', '5000')),
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
    )
