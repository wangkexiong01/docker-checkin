# -*- coding: utf-8 -*-

import logging

import lxml.html

from ..curl import LoginRequest

logger = logging.getLogger(__name__)


class BanyungongRequest(LoginRequest):
    def __init__(self):
        LoginRequest.__init__(self)

        self.tag = '[**banyungong**]'
        self.login_url = 'http://banyungong.org/Login.html'
        self.checkin_url = 'http://banyungong.org/daysign.html'
        self.logout_url = 'http://banyungong.org/'

    def login(self, account, password):
        """
        :param account  - User account
        :param password - User password
        :return:
            None    - login successful with no error
            bla bla - login failed reason
        """

        ret = u'Login Failed'

        resp = self.fetch(self.login_url)
        if self._data.get('code') == 200:
            dom = lxml.html.fromstring(resp)
            hidden = dom.xpath('//input')

            postdata = {'category': 0, 'txtID': account, 'txtPass': password, 'ckbAutoLogin': 'on',
                        'btnLogin': u'登录'.encode('utf-8'),
                        'ucHeader1$txtID': '', 'ucHeader1$txtPass': '', 'ucHeader1$txtSearch': ''}
            for i in hidden:
                if i.name in ['__EVENTTARGET', '__EVENTARGUMENT', '__VIEWSTATE', '__VIEWSTATEGENERATOR',
                              '__EVENTVALIDATION']:
                    postdata[i.name] = i.value

            resp = self.fetch(self.login_url, method='POST', data=postdata)
            if self._data.get('code') == 200 and self._data.get('url') == 'http://banyungong.net/users/index.html':
                ret = None
                logger.info('[banyungong] %s Successfully login ...' % account)
            else:
                dom = lxml.html.fromstring(resp)
                for i in dom.xpath('//span[@id="lblError"]'):
                    if i.text is not None:
                        ret = i.text
                logger.error('[banyungong] %s failed login, reason: %s' % (account, ret))

        return ret

    def checkin(self, str_cookie=None):
        """
        :param str_cookie - Stored Cookie for web access w/o account and password
        :return:
            None        - failed to checkin, possible for cookie expired
                          if the site changed the checkin API, this may None as well
            str of days - already checkin days returned by site
        """

        days = None
        account = None

        if str_cookie is not None:
            logger.debug('[banyungong] Using strcookie: %s', str_cookie)
            self.load_cookie(str_cookie)

        resp = self.fetch(self.checkin_url)
        dom = lxml.html.fromstring(resp)

        user = dom.xpath('//a[@id="ucHeader1_hlkUser"]')
        if len(user) > 0:
            account = user[0].text

        if account is not None:
            signbutton = dom.xpath('//input[@id="btnSign"]')

            if len(signbutton) == 0:
                days = dom.xpath('//span[@id="lblSignDay"]')[0].text
                logger.info('[banyungong] %s is already checkin today with total: %s' % (account, days))
            else:
                logger.debug('[banyungong] %s start to do checkin ...' % account)

                hidden = dom.xpath('//input')
                postdata = {'category': 0, 'btnSign': u'签到'.encode('utf-8'),
                            'ucHeader1$txtSearch': '', '__EVENTARGUMENT': '', '__EVENTTARGET': ''}
                for i in hidden:
                    if i.name in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
                        postdata[i.name] = i.value

                resp = self.fetch(self.checkin_url, method='POST', data=postdata)
                dom = lxml.html.fromstring(resp)
                signresult = dom.xpath('//span[@id="lblSignDay"]')

                if len(signresult) > 0:
                    days = signresult[0].text
                    logger.info('[banyungong] %s checkin with total: %s' % (account, days))
                else:
                    logger.error('[banyungong] %s failed to do checkin ...' % account)
        else:
            logger.info('[banyungong] Cookie Expired ...')

        return days

    def logout(self):
        """
        Logout from website
        """

        resp = self.fetch(self.logout_url)
        dom = lxml.html.fromstring(resp)

        usertag = dom.xpath('//a[@id="ucHeader1_hlkUser"]')
        if len(usertag) > 0:
            user = usertag[0].text
            logger.debug('[banyungong] %s start to logout ...' % user)
            hidden = dom.xpath('//input')
            postdata = {'category': 0, 'ucHeader1$txtSearch': '',
                        '__EVENTTARGET': 'ucHeader1$lkbLoginOut', '__EVENTARGUMENT': ''}
            for i in hidden:
                if i.name in ['__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION']:
                    postdata[i.name] = i.value

            resp = self.fetch(self.logout_url, method='POST', data=postdata)
            dom = lxml.html.fromstring(resp)

            if len(dom.xpath('//a[@id="ucHeader1_hlkUser"]')) > 0:
                logger.error('[banyungong] %s failed to logout ...' % user)
            else:
                logger.info('[banyungong] %s Successfully logout ...' % user)
