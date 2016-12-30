# -*- coding: utf-8 -*-

import json
import logging

import lxml.html

from ..curl import LoginRequest

logger = logging.getLogger(__name__)


class ZimuzuRequest(LoginRequest):
    def __init__(self, yunsodebug=False):
        LoginRequest.__init__(self)

        self.tag = '[**zimuzu**]'
        self.yunso_retry = 5
        self.yunso_showlog = yunsodebug

        self.login_url = 'http://www.zimuzu.tv/User/Login/ajaxLogin'
        self.checkin_url1 = 'http://www.zimuzu.tv/user/sign'
        self.checkin_url2 = 'http://www.zimuzu.tv/user/login/getCurUserTopInfo'
        self.logout_url = 'http://www.zimuzu.tv/user/logout/ajaxLogout'

    def login(self, account, password):
        """
        :param account  - User account
        :param password - User password
        :return:
            None    - login successful with no error
            bla bla - login failed reason
        """

        ret = u'Login Failed'

        postdata = {'account': account, 'password': password, 'remember': 1,
                    'url_back': 'http://www.zimuzu.tv/user/user/index'}
        jsondata = self.fetch_with_yunso(self.login_url, method='POST', data=postdata)

        if self.result.get('code') == 200:
            try:
                resp = json.loads(jsondata)

                if 'status' in resp and resp['status'] == 1:
                    ret = None
                    logger.info('[zimuzu] %s Successfully login ...' % account)
                elif 'info' in resp:
                    ret = resp['info']
                    logger.error('[zimuzu] %s Failed login, info: %s ' % (account, ret))
            except:
                ret = u'Login Failed'
                self.show_yunsuo_redirect(jsondata)

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
            None                - failed to checkin, possible for cookie expired
                                  if the site changed the checkin API, this may None as well
            last 3 checkin days - already checkin days returned by site
        """
        lastcheckin = None
        account = None

        if str_cookie is not None:
            logger.debug('[zimuzu] Using strcookie: %s', str_cookie)
            self.load_cookie(str_cookie)

        resp = self.fetch_with_yunso(self.checkin_url1)
        dom = lxml.html.fromstring(resp)

        userinfo = dom.xpath('//div[@class="a1 tc"]/font[@class="f3"]')
        if len(userinfo) > 0:
            account = userinfo[0].text

        if account is not None:
            jsondata = self.fetch_with_yunso(self.checkin_url2)
            try:
                resp = json.loads(jsondata)

                if resp.get('status') == 1:
                    resp = self.fetch_with_yunso(self.checkin_url1)
                    if self.result.get('code') == 200:
                        dom = lxml.html.fromstring(resp)
                        lastdays = dom.xpath('//div[@class="a2 tc"]/font[@class="f3"]')

                        if len(lastdays) > 0:
                            lastcheckin = lastdays[0].text
                            logger.info('[zimuzu] %s last checkin days: %s' % (account, lastcheckin))
                        else:
                            logger.error('[zimuzu] %s failed to get checkin days ...' % account)
                            self.show_yunsuo_redirect(resp)
                    else:
                        logger.error('[zimuzu] %s failed to checkin ...' % account)
                elif 'info' in resp:
                    ret = resp['info']
                    logger.error('[zimuzu] %s failed checkin, info: %s ' % (account, ret))
            except:
                logger.error('[zimuzu] %s failed to checkin ...' % account)
                self.show_yunsuo_redirect(jsondata)
        else:
            self.show_yunsuo_redirect(resp)

        return lastcheckin

    def fetch_with_yunso(self, url, verifycert=True, method='GET', header=None, data=None, wait=5):
        url += '?security_verify_data=313336362c373638'

        cookie = self.dump_cookie()
        if cookie is None:
            cookie = ""
        import time
        expire = str(int(time.time() + 3600 * 24 * 30 * 30 * 12))
        self.load_cookie(
            cookie + '.zimuzu.tv\tTRUE\t/\tFALSE\t' + expire + '\tsrcurl\t687474703a2f2f7777772e7a696d757a752e74762f\n')

        if header is None:
            header = dict()
        header.update({'Referer': url})

        repeat = True
        times = 0

        while repeat:
            times += 1
            start = int(time.time() * 1000)
            ret = self.fetch(url, verifycert=verifycert, method=method, header=header, data=data, wait=wait)

            passed = int(time.time() * 1000) - start
            if passed < 1 * 1000:
                time.sleep((1 * 1000 - passed) / 1000.0)

            if self.check_yunso_redirect(ret) and times < self.yunso_retry:
                repeat = True
            else:
                repeat = False

        return ret

    def check_yunso_redirect(self, ret):
        return ('YunSuoAutoJump()' in ret) or ('security_verify_data=313' in ret)

    def show_yunsuo_redirect(self, ret):
        if self.yunso_showlog:
            logger.debug('**************************************')
            logger.debug(ret)
            logger.debug('**************************************')
