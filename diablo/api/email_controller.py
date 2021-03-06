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

from diablo.api.errors import BadRequestError, ResourceNotFoundError
from diablo.api.util import admin_required
from diablo.externals.b_connected import BConnected
from diablo.lib.http import tolerant_jsonify
from diablo.merged.emailer import get_email_template_codes, interpolate_email_content
from diablo.models.email_template import EmailTemplate
from diablo.models.queued_email import QueuedEmail
from diablo.models.sent_email import SentEmail
from diablo.models.sis_section import SisSection
from flask import current_app as app, request
from flask_login import current_user


@app.route('/api/email/templates/all')
@admin_required
def get_all_email_templates():
    return tolerant_jsonify([template.to_api_json() for template in EmailTemplate.all_templates()])


@app.route('/api/email/templates/names')
@admin_required
def get_email_templates_names():
    return tolerant_jsonify(EmailTemplate.get_all_templates_names())


@app.route('/api/email/template/<template_id>')
@admin_required
def get_email_template(template_id):
    email_template = EmailTemplate.get_template(template_id)
    if email_template:
        return tolerant_jsonify(email_template.to_api_json())
    else:
        raise ResourceNotFoundError('No such email_template')


@app.route('/api/email/template/delete/<template_id>', methods=['DELETE'])
@admin_required
def delete_email_template(template_id):
    EmailTemplate.delete_template(template_id)
    return tolerant_jsonify({'message': f'Email template {template_id} has been deleted'}), 200


@app.route('/api/email/template/codes')
@admin_required
def get_template_codes():
    return tolerant_jsonify(get_email_template_codes())


@app.route('/api/email/template/create', methods=['POST'])
@admin_required
def create():
    params = request.get_json()
    template_type = params.get('templateType')
    name = params.get('name')
    subject_line = params.get('subjectLine')
    message = params.get('message')

    if None in [template_type, name, subject_line, message]:
        raise BadRequestError('Required parameters are missing.')

    email_template = EmailTemplate.create(
        template_type=template_type,
        name=name,
        subject_line=subject_line,
        message=message,
    )
    return tolerant_jsonify(email_template.to_api_json())


@app.route('/api/email/template/test/<template_id>')
@admin_required
def test_email_template(template_id):
    email_template = EmailTemplate.get_template(template_id)
    if email_template:
        course = SisSection.get_course(term_id=app.config['CURRENT_TERM_ID'], section_id='12597')
        template = EmailTemplate.get_template(template_id)
        subject_line = interpolate_email_content(
            course=course,
            recipient_name=current_user.name,
            templated_string=template.subject_line,
        )
        message = interpolate_email_content(
            course=course,
            recipient_name=current_user.name,
            templated_string=template.message,
        )
        BConnected().send(
            recipients=[
                {
                    'email': current_user.email_address,
                    'name': current_user.name,
                    'uid': current_user.uid,
                },
            ],
            message=message,
            subject_line=subject_line,
        )
        return tolerant_jsonify({'message': f'Email sent to {current_user.email_address}'}), 200
    else:
        raise ResourceNotFoundError('No such email_template')


@app.route('/api/email/template/update', methods=['POST'])
@admin_required
def update():
    params = request.get_json()
    template_id = params.get('templateId')
    email_template = EmailTemplate.get_template(template_id) if template_id else None
    if email_template:
        template_type = params.get('templateType')
        name = params.get('name')
        subject_line = params.get('subjectLine')
        message = params.get('message')

        if None in [template_type, name, subject_line, message]:
            raise BadRequestError('Required parameters are missing.')

        email_template = EmailTemplate.update(
            template_id=template_id,
            template_type=template_type,
            name=name,
            subject_line=subject_line,
            message=message,
        )
        return tolerant_jsonify(email_template.to_api_json())
    else:
        raise ResourceNotFoundError('No such email template')


@app.route('/api/emails/queue', methods=['POST'])
@admin_required
def queue_emails():
    params = request.get_json()
    term_id = params.get('termId')
    section_ids = params.get('sectionIds')
    template_type = params.get('emailTemplateType')

    if term_id and section_ids and template_type:
        section_ids_already_queued = QueuedEmail.get_all_section_ids(template_type=template_type, term_id=term_id)
        section_ids_to_queue = [id_ for id_ in section_ids if id_ not in section_ids_already_queued]

        for section_id in section_ids_to_queue:
            QueuedEmail.create(section_id=section_id, template_type=template_type, term_id=term_id)

        section_id_count = len(section_ids)
        queued_count = len(section_ids_to_queue)
        if queued_count < section_id_count:
            message = f"""
                {len(section_ids_already_queued)} '{template_type}' emails were already queued up for the
                {'course' if section_id_count == 1 else 'courses'} you submitted.
                Thus, {'no' if queued_count == 0 else f'only {queued_count}'} emails added to the queue.
            """
        else:
            message = f'{queued_count} \'{template_type}\' emails will be sent.'
        return tolerant_jsonify({
            'message': message,
        })
    else:
        raise BadRequestError('Required parameters are missing.')


@app.route('/api/emails/sent/<uid>')
@admin_required
def get_emails_sent_to_uid(uid):
    return tolerant_jsonify([e.to_api_json() for e in SentEmail.get_emails_sent_to(uid)])
