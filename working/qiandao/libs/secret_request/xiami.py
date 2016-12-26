# -*- coding: utf-8 -*-

import logging

import lxml.html

from ..curl import LoginRequest

logger = logging.getLogger(__name__)


class XiamiRequest(LoginRequest):
    def __init__(self):
        LoginRequest.__init__(self)

        self.tag = '[**xiami**]'
        self.login_url = 'https://login.xiami.com/web/login'
        self.checkin_url = 'http://www.xiami.com/web/checkin/id/'
        self.logout_url = 'http://www.xiami.com/member/logout?from=mobile'

    def login(self, account, password):
        """
        :param account  - User account
        :param password - User password
        :return:
            None    - login successful with no error
            bla bla - login failed reason
        """

        ret = u'Login Failed'

        postdata = {'email': account, 'password': password, 'remember': 1, 'LoginButton': u'登录'.encode('utf-8')}
        resp = self.fetch(self.login_url, method='POST', data=postdata)

        if self._data.get('code') == 200:
            if self._data.get('url') == 'http://www.xiami.com/web/profile':
                ret = None
                logger.info('[xiami] Successfully login for %s' % account)
            else:
                dom = lxml.html.fromstring(resp)
                info = dom.xpath('//div[@class="land"]/p/b')
                if len(info) > 0:
                    logger.error('[xiami] %s failed to login, reason: %s' % (account, ret))
                    ret = info[0].text
                else:
                    logger.error('[xiami] is not accessible...')

        return ret

    def logout(self):
        """
        If we have session cookie, call logout to fresh cookies.
        Seems we can clean cookie instead...
        """
        if self.cookie is not None:
            self.fetch(self.logout_url)

    def checkin(self, str_cookie=None):
        """
        :param str_cookie - Stored Cookie for web access w/o account and password
        :return:
            None        - failed to checkin, possible for cookie expired
                          if the site changed the checkin API, this may None as well
            str of days - already checkin days returned by site
        """
        days = None
        xiamiID = None

        if str_cookie is not None:
            logger.debug('[xiami] Using strcookie: %s', str_cookie)
            self.load_cookie(str_cookie)

        if self.cookie is not None:
            for cookie in self.cookie:
                if cookie.name == 'user':
                    xiamiID = cookie.value.split('%22')[0]
                    logger.debug('[xiami] Extract cookie while doing checkin and get UserID: %s' % xiamiID)

        if xiamiID is not None:
            url = self.checkin_url + xiamiID
            logger.debug('[xiami] Compose checkin url: %s', url)

            times = 0
            repeat = True
            while repeat:
                header = {'Referer': 'http://www.xiami.com/web'}
                resp = self.fetch(url, header=header)

                dom = lxml.html.fromstring(resp)
                for i in dom.xpath('//div[@class="idh"]'):
                    if i.text is not None:
                        days = i.text

                times += 1
                if days is None and times < 2:
                    logger.info('[xiami] Retry with updated cookie for UserID: %s' % xiamiID)
                    repeat = True
                else:
                    repeat = False

            logger.info('[xiami] %s checkin days: %s' % (xiamiID, days))
        else:
            logger.error('[xiami] No XiamiID can be got from cookie ...')

        return days
