# -*- coding: utf-8 -*-

import logging

import lxml.html

from ..curl import LoginRequest

logger = logging.getLogger(__name__)


class PacktRequest(LoginRequest):
    def __init__(self):
        LoginRequest.__init__(self)

        self.tag = '[**packtpub**]'
        self.web_root = 'https://www.packtpub.com'
        self.login_url = 'https://www.packtpub.com'
        self.checkin_url = 'https://www.packtpub.com/packt/offers/free-learning'
        self.logout_url = 'https://www.packtpub.com/logout'

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
            hidden = dom.xpath('//form[@id="packt-user-login-form"]/div/input')

            postdata = {'op': 'Login', 'email': account, 'password': password}
            for i in hidden:
                postdata[i.name] = i.value

            resp = self.fetch(self.login_url, method='POST', data=postdata)
            if self._data.get('code') == 200:
                dom = lxml.html.fromstring(resp)
                if len(dom.xpath('//form[@id="packt-user-login-form"]/div/input[@name="form_token"]')) == 1:
                    ret = None
                    logger.info('[packtpub] %s Successfully login ...' % account)
                else:
                    ret = "EMAIL/PASSWORD Verify failed..."
                    logger.error('[packtpub] %s failed login, reason: %s' % (account, ret))

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
            None        - Failed to get daily offer, possible for cookie expired
                          if the site changed the checkin API, this may None as well
            book name   - Daily free offer book
        """
        book = None

        if str_cookie is not None:
            logger.debug('[packtpub] Using strcookie: %s', str_cookie)
            self.load_cookie(str_cookie)

        resp = self.fetch(self.checkin_url)
        dom = lxml.html.fromstring(resp)
        if len(dom.xpath('//form[@id="packt-user-login-form"]/div/input[@name="form_token"]')) == 1:
            times = 0
            repeat = True

            while repeat:
                offer = dom.xpath('//div[@class="dotd-title"]/h2')
                if len(offer) > 0:
                    book = offer[0].text.strip()
                    href_element = dom.xpath('//div[@class="float-left free-ebook"]/a')
                    if len(href_element) > 0:
                        book_url = self.web_root + href_element[0].attrib['href']
                        resp = self.fetch(book_url)
                        times += 1

                        if self._data.get('url') == 'https://www.packtpub.com/account/my-ebooks':
                            logger.info('[packtpub] Acquire Free EBook: %s' % book)
                            repeat = False
                        elif times < 2:
                            logger.info('[packtpub] Retry with refresh web page...')
                            if resp is not '':
                                dom = lxml.html.fromstring(resp)
                        else:
                            repeat = False
                            book = None
                            logger.error("[packtpub] failed to acquire today's Free EBook...")

        return book
