# -*- coding: utf-8 -*-

import logging
from email.mime.text import MIMEText
from smtplib import SMTPException, SMTPAuthenticationError
from smtplib import SMTP_SSL as SMTP

logger = logging.getLogger(__name__)


class MailSMTPPool(object):
    def __init__(self):
        self.resource = list()
        self.total = 0
        self.index = 0

    def add_resource(self, server, sender, pwd):
        conn = SMTP()

        code, _ = conn.connect(server)
        if code != 220:
            logger.debug('SMTP: %s is not accessible ...' % server)
            return False

        try:
            conn.login(sender, pwd)
        except SMTPAuthenticationError:
            logger.debug('SMTP: %s authenticate failed ...' % server)
            return False
        except SMTPException as e:
            logger.debug('SMTP: %s throw exception %s' % (server, e.message))
            return False
        finally:
            conn.quit()

        logger.debug('SMTP: Resource %s(%s) added ...' % (server, sender))
        self.resource.append((server, sender, pwd))
        self.total += 1
        return True

    def get_resource(self):
        if self.total > 0:
            current = self.index
            self.index += 1
            if self.index >= self.total:
                self.index = 0

            return self.resource[current]
        else:
            return None

    def send(self, rcpt, msg):
        if self.total > 0:
            server, sender, pwd = self.get_resource()

            content = None
            if isinstance(msg, basestring):
                content = MIMEText(msg, 'plain', 'utf8')
                content['From'] = u'Lazy<%s>' % sender
                content['To'] = rcpt
                content['Subject'] = 'FYI'
            if isinstance(msg, MIMEText):
                content = msg

            if content is not None:
                conn = SMTP()
                try:
                    conn.connect(server)
                    conn.login(sender, pwd)
                    error = conn.sendmail(sender, rcpt, content.as_string())
                    if not error:
                        return False

                    return True
                except SMTPException as e:
                    logger.debug('Error happened while sending email: %s' % e.message)
                    return False
                finally:
                    conn.quit()
            else:
                logger.debug('Body is not accepted ...')
                return False
        else:
            logger.debug('No Resource available ...')
            return False
