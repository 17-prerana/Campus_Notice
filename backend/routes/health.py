"""Health-check routes."""

from flask import Blueprint, jsonify


health_bp = Blueprint('health', __name__)


@health_bp.get('/api/health')
def health_check():
    """Report that the API is available without revealing configuration."""
    return jsonify({
        'success': True,
        'message': 'College Notice Assistant API is running',
        'status': 'healthy',
    }), 200
