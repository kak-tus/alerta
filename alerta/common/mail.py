
import os
import json
import smtplib
import datetime
import uuid

import pytz

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from alerta.common import log as logging
from alerta.common import config

LOG = logging.getLogger(__name__)
CONF = config.CONF


class Mail(object):

    def __init__(self, alert):

        # Convert createTime to local time (set TIMEZONE above)
        createTime = datetime.datetime.strptime(alert['createTime'], '%Y-%m-%dT%H:%M:%S.%fZ')
        createTime = createTime.replace(tzinfo=pytz.utc)
        tz = pytz.timezone(CONF.timezone)
        localTime = createTime.astimezone(tz)

        text = ''
        text += '[%s] %s\n' % (alert['status'], alert['summary'])
        text += 'Alert Details\n'
        text += 'Alert ID: %s\n' % (alert['id'])
        text += 'Create Time: %s\n' % (localTime.strftime('%Y/%m/%d %H:%M:%S'))
        text += 'Resource: %s\n' % (alert['resource'])
        text += 'Environment: %s\n' % (','.join(alert['environment']))
        text += 'Service: %s\n' % (','.join(alert['service']))
        text += 'Event Name: %s\n' % (alert['event'])
        text += 'Event Group: %s\n' % (alert['group'])
        text += 'Event Value: %s\n' % (alert['value'])
        text += 'Severity: %s -> %s\n' % (alert['previousSeverity'], alert['severity'])
        text += 'Status: %s\n' % (alert['status'])
        text += 'Text: %s\n' % (alert['text'])
        if 'thresholdInfo' in alert:
            text += 'Threshold Info: %s\n' % (alert['thresholdInfo'])
        if 'duplicateCount' in alert:
            text += 'Duplicate Count: %s\n' % (alert['duplicateCount'])
        if 'moreInfo' in alert:
            text += 'More Info: %s\n' % (alert['moreInfo'])
        text += 'Historical Data\n'
        if 'graphs' in alert:
            for g in alert['graphs']:
                text += '%s\n' % (g)
        text += 'Raw Alert\n'
        text += '%s\n' % (json.dumps(alert))
        text += 'Generated by %s on %s at %s\n' % (
            'alert-mailer.py', os.uname()[1], datetime.datetime.now().strftime("%a %d %b %H:%M:%S"))

        LOG.debug('Raw Text: %s', text)

        html = '<p><table border="0" cellpadding="0" cellspacing="0" width="100%">\n'  # table used to center email
        html += '<tr><td bgcolor="#ffffff" align="center">\n'
        html += '<table border="0" cellpadding="0" cellspacing="0" width="700">\n'     # table used to set width of email
        html += '<tr><td bgcolor="#425470"><p align="center" style="font-size:24px;color:#d9fffd;font-weight:bold;"><strong>[%s] %s</strong></p>\n' % (
            alert['status'], alert['summary'])

        html += '<tr><td><p align="left" style="font-size:18px;line-height:22px;color:#c25130;font-weight:bold;">Alert Details</p>\n'
        html += '<table>\n'
        html += '<tr><td><b>Alert ID:</b></td><td><a href="http://%s:%s/alerta/details.php?id=%s" target="_blank">%s</a></td></tr>\n' % (
            CONF.api_host, CONF.api_port, alert['id'], alert['id'])  # TODO(nsatterl): make web UI console location a CONF option
        html += '<tr><td><b>Create Time:</b></td><td>%s</td></tr>\n' % (localTime.strftime('%Y/%m/%d %H:%M:%S'))
        html += '<tr><td><b>Resource:</b></td><td>%s</td></tr>\n' % (alert['resource'])
        html += '<tr><td><b>Environment:</b></td><td>%s</td></tr>\n' % (','.join(alert['environment']))
        html += '<tr><td><b>Service:</b></td><td>%s</td></tr>\n' % (','.join(alert['service']))
        html += '<tr><td><b>Event Name:</b></td><td>%s</td></tr>\n' % (alert['event'])
        html += '<tr><td><b>Event Group:</b></td><td>%s</td></tr>\n' % (alert['group'])
        html += '<tr><td><b>Event Value:</b></td><td>%s</td></tr>\n' % (alert['value'])
        html += '<tr><td><b>Severity:</b></td><td>%s -> %s</td></tr>\n' % (alert['previousSeverity'], alert['severity'])
        html += '<tr><td><b>Status:</b></td><td>%s</td></tr>\n' % (alert['status'])
        html += '<tr><td><b>Text:</b></td><td>%s</td></tr>\n' % (alert['text'])
        if 'thresholdInfo' in alert:
            html += '<tr><td><b>Threshold Info:</b></td><td>%s</td></tr>\n' % (alert['thresholdInfo'])
        if 'duplicateCount' in alert:
            html += '<tr><td><b>Duplicate Count:</b></td><td>%s</td></tr>\n' % (alert['duplicateCount'])
        if 'moreInfo' in alert:
            html += '<tr><td><b>More Info:</b></td><td><a href="%s">ganglia</a></td></tr>\n' % (alert['moreInfo'])
        html += '</table>\n'
        html += '</td></tr>\n'
        html += '<tr><td><p align="left" style="font-size:18px;line-height:22px;color:#c25130;font-weight:bold;">Historical Data</p>\n'
        if 'graphs' in alert:
            graph_cid = dict()
            for g in alert['graphs']:
                graph_cid[g] = str(uuid.uuid4())
                html += '<tr><td><img src="cid:' + graph_cid[g] + '"></td></tr>\n'
        html += '<tr><td><p align="left" style="font-size:18px;line-height:22px;color:#c25130;font-weight:bold;">Raw Alert</p>\n'
        html += '<tr><td><p align="left" style="font-family: \'Courier New\', Courier, monospace">%s</p></td></tr>\n' % (
            json.dumps(alert))
        html += '<tr><td>Generated by %s on %s at %s</td></tr>\n' % (
            'alert-mailer.py', os.uname()[1], datetime.datetime.now().strftime("%a %d %b %H:%M:%S"))
        html += '</table>'
        html += '</td></tr></table>'
        html += '</td></tr></table>'

        LOG.debug('HTML Text %s', html)

        self.subject = ''
        self.text = text
        self.html = html

    def send(self):

        msg_root = MIMEMultipart('related')
        msg_root['Subject'] = self.subject
        msg_root['From'] = CONF.mail_user
        msg_root['To'] = ','.join(CONF.mail_list)
        msg_root.preamble = 'This is a multi-part message in MIME format.'

        msg_alt = MIMEMultipart('alternative')
        msg_root.attach(msg_alt)

        msg_text = MIMEText(self.text, 'plain')
        msg_alt.attach(msg_text)

        msg_html = MIMEText(self.html, 'html')
        msg_alt.attach(msg_html)

        # TODO(nsatterl): add graphs to emails
        # if 'graphs' in alert:
        #     msg_img = dict()
        #     for g in alert['graphs']:
        #         try:
        #             image = urllib2.urlopen(g).read()
        #             msg_img[g] = MIMEImage(image)
        #             LOG.debug('graph cid %s', graph_cid[g])
        #             msg_img[g].add_header('Content-ID', '<' + graph_cid[g] + '>')
        #             msg_root.attach(msg_img[g])
        #         except:
        #             pass

        try:
            mail_exchange = smtplib.SMTP(CONF.smtp_host)
            #DEBUG mail_exchange.set_debuglevel(1)
            mail_exchange.sendmail(CONF.mail_user, CONF.mail_list, msg_root.as_string())
            mail_exchange.quit()

        except smtplib.SMTPException, e:
            LOG.error('Failed to send mail to %s:%s : %s', CONF.mail_host, CONF.mail_port, e)



