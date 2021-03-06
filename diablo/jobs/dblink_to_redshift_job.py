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
from diablo.externals.rds import execute
from diablo.jobs.background_job_manager import BackgroundJobError
from diablo.jobs.base_job import BaseJob
from diablo.jobs.util import insert_or_update_instructors, refresh_rooms
from diablo.lib.db import resolve_sql_template
from diablo.models.cross_listing import CrossListing
from diablo.models.sis_section import SisSection
from flask import current_app as app


class DblinkToRedshiftJob(BaseJob):

    def run(self, args=None):
        resolved_ddl_rds = resolve_sql_template('update_rds_sis_sections.template.sql')
        if execute(resolved_ddl_rds):
            distinct_instructor_uids = SisSection.get_distinct_instructor_uids()
            insert_or_update_instructors(distinct_instructor_uids)
            app.logger.info(f'{len(distinct_instructor_uids)} instructors updated')

            term_id = app.config['CURRENT_TERM_ID']
            CrossListing.refresh(term_id=term_id)
            app.logger.info('\'cross_listings\' table refreshed')

            refresh_rooms()
            app.logger.info('RDS indexes updated.')
        else:
            raise BackgroundJobError('Failed to update RDS indexes for intermediate schema.')

    @classmethod
    def description(cls):
        return 'Get latest course, instructor and room data from the Data Lake.'
