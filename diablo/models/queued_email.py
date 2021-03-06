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

from datetime import datetime

from diablo import db, std_commit
from diablo.lib.util import to_isoformat
from diablo.models.email_template import email_template_type, EmailTemplate


class QueuedEmail(db.Model):
    __tablename__ = 'queued_emails'

    id = db.Column(db.Integer, nullable=False, primary_key=True)  # noqa: A003
    section_id = db.Column(db.Integer, nullable=False)
    template_type = db.Column(email_template_type, nullable=False)
    term_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    __table_args__ = (db.UniqueConstraint(
        'section_id',
        'template_type',
        'term_id',
        name='queued_emails_section_id_template_type_unique_constraint',
    ),)

    def __init__(self, section_id, template_type, term_id):
        self.template_type = template_type
        self.section_id = section_id
        self.term_id = term_id

    def __repr__(self):
        return f"""<QueuedEmail
                    id={self.id}
                    section_id={self.section_id},
                    template_type={self.template_type}
                    term_id={self.term_id},
                    created_at={self.created_at}
                """

    @classmethod
    def create(cls, section_id, template_type, term_id):
        queued_email = cls(
            section_id=section_id,
            template_type=template_type,
            term_id=term_id,
        )
        db.session.add(queued_email)
        std_commit()
        return queued_email

    @classmethod
    def delete(cls, queued_email):
        db.session.delete(queued_email)
        std_commit()

    @classmethod
    def get_all(cls, term_id):
        return cls.query.filter_by(term_id=term_id).order_by(cls.created_at).all()

    @classmethod
    def get_all_section_ids(cls, template_type, term_id):
        return [row.section_id for row in cls.query.filter_by(template_type=template_type, term_id=term_id).all()]

    def to_api_json(self):
        return {
            'id': self.id,
            'sectionId': self.section_id,
            'templateType': self.template_type,
            'templateTypeName': EmailTemplate.get_template_type_options()[self.template_type],
            'termId': self.term_id,
            'createdAt': to_isoformat(self.created_at),
        }
