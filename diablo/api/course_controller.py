"""
Copyright ©2020. The Regents of the University of California (Regents). All Rights Reserved.

Permission to use, copy, modify, and distribute this software and its documentation
for educational, research, and not-for-profit purposes, without fee and without a
signed licensing agreement, is hereby granted, provided that the above copyright
notice, this paragraph and the following two paragraphs appear in all copies,
modifications, and distributions.

Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.

IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.

REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
"AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
ENHANCEMENTS, OR MODIFICATIONS.
"""

from diablo.api.errors import BadRequestError, ForbiddenRequestError, ResourceNotFoundError
from diablo.api.util import admin_required, get_search_filter_options
from diablo.lib.berkeley import get_instructor_uids, has_necessary_approvals, term_name_for_sis_id
from diablo.lib.http import tolerant_jsonify
from diablo.lib.util import objects_to_dict_organized_by_section_id
from diablo.merged.emailer import notify_instructors_of_approval
from diablo.merged.sis import get_course, get_courses
from diablo.models.approval import Approval, get_all_publish_types, get_all_recording_types, NAMES_PER_PUBLISH_TYPE
from diablo.models.course_preference import CoursePreference
from diablo.models.room import Room
from diablo.models.scheduled import Scheduled
from flask import current_app as app, request
from flask_login import current_user, login_required


@app.route('/api/course/approve', methods=['POST'])
@login_required
def approve():
    term_id = app.config['CURRENT_TERM_ID']
    term_name = term_name_for_sis_id(term_id)

    params = request.get_json()
    publish_type = params.get('publishType')
    recording_type = params.get('recordingType')
    section_id = params.get('sectionId')
    course = get_course(term_id, section_id) if section_id else None

    if not course or publish_type not in get_all_publish_types() or recording_type not in get_all_recording_types():
        raise BadRequestError('One or more required params are missing or invalid')

    if not current_user.is_admin and current_user.uid not in [i['uid'] for i in course['instructors']]:
        raise ForbiddenRequestError('Sorry, request unauthorized')

    if Approval.get_approval(current_user.uid, section_id, term_id):
        raise ForbiddenRequestError(f'You have already approved recording of {course["courseName"]}, {term_name}')

    location = course['meetingLocation']
    room = Room.find_room(location=location)
    if not room:
        raise BadRequestError(f'{location} is not eligible for Course Capture.')

    previous_approvals = Approval.get_approvals_per_section_ids(section_ids=[section_id], term_id=term_id)
    approval = Approval.create(
        approved_by_uid=current_user.uid,
        section_id=section_id,
        term_id=term_id,
        approver_type_='admin' if current_user.is_admin else 'instructor',
        publish_type_=publish_type,
        recording_type_=recording_type,
        room_id=room.id,
    )
    _notify_instructors_of_approval(
        approval=approval,
        course=course,
        previous_approvals=previous_approvals,
    )
    return tolerant_jsonify(_course_to_json(course, term_id))


@app.route('/api/course/approvals/<term_id>/<section_id>')
@login_required
def get_approvals(term_id, section_id):
    section = get_course(term_id, section_id)
    if not section:
        raise ResourceNotFoundError(f'No section for term_id = {term_id} and section_id = {section_id}')

    if not current_user.is_admin and current_user.uid not in get_instructor_uids(section):
        raise ForbiddenRequestError('Sorry, this request is unauthorized.')
    return tolerant_jsonify(_course_to_json(section, term_id))


@app.route('/api/courses', methods=['POST'])
@admin_required
def courses():
    params = request.get_json()
    term_id = params.get('termId')
    filter_option = params.get('filter', 'Not Invited')
    if filter_option not in get_search_filter_options() or not term_id:
        raise BadRequestError('One or more required params are missing or invalid')

    api_json = []
    approvals_per_section_id = objects_to_dict_organized_by_section_id(objects=Approval.get_approvals_per_term(term_id))
    scheduled_per_section_id = objects_to_dict_organized_by_section_id(objects=Scheduled.get_all_scheduled(term_id))
    section_ids = set(approvals_per_section_id.keys()).union(set(scheduled_per_section_id.keys()))

    for course in get_courses(term_id, section_ids):
        section_id = int(course['sectionId'])
        course['approvals'] = [a.to_api_json() for a in approvals_per_section_id.get(section_id, [])]
        room = Room.find_room(course['meetingLocation'])
        course['room'] = room and room.to_api_json()
        course['scheduled'] = [s.to_api_json() for s in scheduled_per_section_id.get(section_id, [])]
        api_json.append(course)
    return tolerant_jsonify(api_json)


@app.route('/api/course/opt_out/update', methods=['POST'])
@admin_required
def update_opt_out():
    params = request.get_json()
    term_id = params.get('termId')
    section_id = params.get('sectionId')
    opt_out = params.get('optOut')
    preferences = CoursePreference.update_opt_out(
        term_id=term_id,
        section_id=section_id,
        opt_out=opt_out,
    )
    return tolerant_jsonify(preferences.to_api_json())


def _approvals_per_section(term_id):
    approvals_per_section_id = {}
    for approval in Approval.get_approvals_per_term(term_id):
        section_id = approval.section_id
        if section_id not in approvals_per_section_id:
            approvals_per_section_id[section_id] = []
        approvals_per_section_id[section_id].append(approval.to_api_json())

    api_json = []
    section_ids = list(approvals_per_section_id.keys())
    for course in get_courses(term_id, section_ids):
        section_id = course['sectionId']
        course['approvals'] = approvals_per_section_id[section_id] if section_id in approvals_per_section_id else []
        api_json.append(course)
    return api_json


def _course_to_json(section, term_id):
    room = Room.find_room(section['meetingLocation'])
    section_id = section['sectionId']
    all_approvals = Approval.get_approvals_per_section_ids(section_ids=[section_id], term_id=term_id)
    return {
        'approvals': [approval.to_api_json() for approval in all_approvals],
        'hasNecessaryApprovals': has_necessary_approvals(section, all_approvals),
        'publishTypeOptions': NAMES_PER_PUBLISH_TYPE,
        'room': room.to_api_json(),
        'scheduled': Scheduled.was_scheduled(section_id=section_id, term_id=term_id),
        'section': section,
        'termId': term_id,
    }


def _notify_instructors_of_approval(approval, course, previous_approvals):
    type_of_sent_email = None
    if previous_approvals:
        # Compare the current approval with preferences submitted in previous approval
        previous_approval = previous_approvals[-1]
        previous_publish_type = previous_approval.publish_type
        previous_recording_type = previous_approval.recording_type
        if approval.publish_type != previous_publish_type or approval.recording_type != previous_recording_type:
            type_of_sent_email = 'notify_instructor_of_changes'
            notify_instructors_of_approval(
                course=course,
                latest_approval=approval,
                name_of_latest_approver=current_user.name,
                previous_publish_type=previous_publish_type,
                previous_recording_type=previous_recording_type,
                template_type=type_of_sent_email,
                term_id=course['termId'],
            )
    all_approvals = previous_approvals + [approval]
    if not type_of_sent_email and len(course['instructors']) > len(all_approvals):
        approval_uids = [a.approved_by_uid for a in all_approvals]
        type_of_sent_email = 'waiting_for_approval'
        notify_instructors_of_approval(
            pending_instructors=[i for i in course['instructors'] if i['uid'] not in approval_uids],
            course=course,
            latest_approval=approval,
            name_of_latest_approver=current_user.name,
            template_type=type_of_sent_email,
            term_id=course['termId'],
        )
    return type_of_sent_email
