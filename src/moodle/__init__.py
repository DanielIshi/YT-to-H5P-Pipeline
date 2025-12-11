# Moodle API Services
from .course_image import (
    set_course_image,
    set_course_image_from_youtube,
    set_course_image_generated,
    upload_course_image
)

__all__ = [
    'set_course_image',
    'set_course_image_from_youtube',
    'set_course_image_generated',
    'upload_course_image'
]
