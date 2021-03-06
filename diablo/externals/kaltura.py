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

from diablo import cachify, skip_when_pytest
from flask import current_app as app
from KalturaClient import KalturaClient, KalturaConfiguration
from KalturaClient.Plugins.Core import KalturaFilterPager, KalturaMediaEntryFilter
from KalturaClient.Plugins.Schedule import KalturaScheduleEvent, KalturaScheduleEventClassificationType, \
    KalturaScheduleEventRecurrence, KalturaScheduleEventRecurrenceFrequency, KalturaScheduleEventRecurrenceType, \
    KalturaScheduleEventStatus, KalturaScheduleResourceFilter, KalturaSessionType


class Kaltura:

    def __init__(self):
        self.kaltura_partner_id = app.config['KALTURA_PARTNER_ID']
        if app.config['DIABLO_ENV'] == 'test':
            return

    def __del__(self):
        # TODO: Close Kaltura client connection?
        pass

    @cachify('kaltura/get_resource_list', timeout=30)
    def get_resource_list(self):
        response = self.kaltura_client.schedule.scheduleResource.list(
            KalturaScheduleResourceFilter(),
            KalturaFilterPager(),
        )
        return [{'id': o.id, 'name': o.name} for o in response.objects]

    @skip_when_pytest()
    def schedule_recording(
            self,
            course_label,
            instructor_uids,
            days,
            start_time,
            end_time,
            publish_type,
            recording_type,
            room,
    ):
        description = f"""
            {course_label} meets in {room.location}, {start_time} - {end_time} on {days}.
            Recordings of type {recording_type} will be published to {publish_type}.
        """
        utc_now_timestamp = datetime.utcnow().timestamp()

        skip_kaltura_integration = True

        if skip_kaltura_integration:
            return []
        else:
            # https://developer.kaltura.com/api-docs/General_Objects/Objects/KalturaScheduleEvent
            recurring_event = KalturaScheduleEvent(
                # TODO: Which KalturaScheduleEventClassificationType do we want?
                classificationType=KalturaScheduleEventClassificationType.PRIVATE_EVENT,
                # Specifies non-processing information intended to provide a comment to the calendar user.
                comment=f'Recordings for {course_label} scheduled by Diablo.',
                # Used to represent contact information or alternately a reference to contact information.
                contact=f'Instructor UIDs: {",".join(instructor_uids)}',
                # Creation date as Unix timestamp, in seconds
                createdAt=utc_now_timestamp,
                description=description.strip(),
                # Duration in seconds. TODO: Is duration
                duration=NotImplemented,
                endDate=datetime.strptime(app.config['CURRENT_TERM_END'], '%Y-%m-%d').timestamp(),
                # Specifies the global position for the activity. TODO: Do we care?
                geoLatitude=NotImplemented,
                # Specifies the global position for the activity. TODO: Do we care?
                geoLongitude=NotImplemented,
                # Defines the intended venue for the activity. TODO: Which arg gets room.kaltura_resource_id?
                location=NotImplemented,
                # TODO: Is 'organizer' admin or instructor? I believe the field wants an email address.
                organizer=app.config['EMAIL_DIABLO_ADMIN'],
                # TODO: What is proper ownerId? The following is based on test recordings scheduled by Ops.
                ownerId='kmsAdminServiceUser',
                # TODO: What is parentId?
                parentId=NotImplemented,
                partnerId=self.kaltura_partner_id,
                priority=NotImplemented,
                # https://developer.kaltura.com/api-docs/General_Objects/Objects/KalturaScheduleEventRecurrence
                recurrence=KalturaScheduleEventRecurrence(
                    # Comma separated of KalturaScheduleEventRecurrenceDay Each byDay value can also be preceded by a
                    # positive (+n) or negative (-n) integer. If present, this indicates the nth occurrence of the
                    # specific day within the MONTHLY or YEARLY RRULE. For example, within a MONTHLY rule,
                    # +1MO (or simply 1MO) represents the first Monday within the month, whereas -1MO represents the last
                    # Monday of the month. If an integer modifier is not present, it means all days of this type within
                    # the specified frequency. For example, within a MONTHLY rule, MO represents all Mondays within
                    # the month.
                    byDay=','.join(days),
                    # Comma separated numbers between 0 to 23
                    byHour=NotImplemented,
                    # Comma separated numbers between 0 to 59
                    byMinute=NotImplemented,
                    # Comma separated numbers between 1 to 12
                    byMonth=NotImplemented,
                    # Comma separated of numbers between -31 to 31, excluding 0.
                    # For example, -10 represents the tenth to the last day of the month.
                    byMonthDay=NotImplemented,
                    # Comma separated of numbers between -366 to 366, excluding 0. Corresponds to the nth occurrence within
                    # the set of events specified by the rule. It must only be used in conjunction with another byrule part.
                    # For example "the last work day of the month" could be represented as:
                    #   frequency=MONTHLY;byDay=MO,TU,WE,TH,FR;byOffset=-1
                    # Each byOffset value can include a positive (+n) or negative (-n) integer. If present, this indicates
                    # the nth occurrence of the specific occurrence within the set of events specified by the rule.
                    byOffset=NotImplemented,
                    # Comma separated numbers between 0 to 59
                    bySecond=NotImplemented,
                    # Comma separated of numbers between -53 to 53, excluding 0. This corresponds to weeks according to
                    # week numbering. A week is defined as a seven day period, starting on the day of the week defined to
                    # be the week start. Week number one of the calendar year is the first week which contains at least
                    # four (4) days in that calendar year. This rule part is only valid for YEARLY frequency.
                    # For example, 3 represents the third week of the year.
                    byWeekNumber=NotImplemented,
                    # Comma separated of numbers between -366 to 366, excluding 0. For example, -1 represents the last day
                    # of the year (December 31st) and -306 represents the 306th to the last day of the year (March 1st).
                    byYearDay=NotImplemented,
                    count=NotImplemented,
                    frequency=KalturaScheduleEventRecurrenceFrequency.WEEKLY,
                    # TODO: I think 'interval' is important. What is it?
                    interval=NotImplemented,
                    name=NotImplemented,
                    timeZone='US/Pacific',
                    until=NotImplemented,
                    weekStartDay=days[0],  # See KalturaScheduleEventRecurrenceDay enum
                ),
                recurrenceType=KalturaScheduleEventRecurrenceType.RECURRING,
                # TODO: 'referenceId' seems important. What is it?
                referenceId=NotImplemented,
                sequence=NotImplemented,
                startDate=datetime.strptime(app.config['CURRENT_TERM_BEGIN'], '%Y-%m-%d').timestamp(),
                status=KalturaScheduleEventStatus.ACTIVE,
                # TODO: How is 'summary' different than 'description' and 'comment'?
                summary=NotImplemented,
                # TODO: Tags?
                tags=NotImplemented,
                # updatedAt=NotImplemented,
            )
            response = self.kaltura_client.schedule.scheduleResource.add(recurring_event)
            return [{'id': o.id, 'name': o.name} for o in response.objects]

    def ping(self):
        filter_ = KalturaMediaEntryFilter()
        filter_.nameLike = 'Love is the drug I\'m thinking of'
        result = self.kaltura_client.media.list(filter_, KalturaFilterPager(pageSize=1))
        return result.totalCount is not None

    @property
    def kaltura_client(self):
        admin_secret = app.config['KALTURA_ADMIN_SECRET']
        unique_user_id = app.config['KALTURA_UNIQUE_USER_ID']
        partner_id = self.kaltura_partner_id
        expiry = app.config['KALTURA_EXPIRY']

        config = KalturaConfiguration()
        client = KalturaClient(config)
        ks = client.session.start(
            admin_secret,
            unique_user_id,
            KalturaSessionType.ADMIN,
            partner_id,
            expiry,
            'appId:appName-appDomain',
        )
        client.setKs(ks)
        return client
