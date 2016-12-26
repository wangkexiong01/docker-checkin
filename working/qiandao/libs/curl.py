# -*- coding:utf-8 -*-

import json
import logging
import ssl
import urllib
import urllib2
import urlparse
import zlib

import strcookiejar

logger = logging.getLogger(__name__)


class LoginRequest(object):
    def __init__(self):
        self.cookie = None
        self.opener = None
        self._data = None

    def clear_cookie(self):
        logging.info('Clear Cookie ...')
        self.cookie = None
        self.opener = None

    def load_cookie(self, cookie):
        if isinstance(cookie, str):
            logging.info('Load Cookie ...')
            self.cookie = strcookiejar.StrCookieJar(cookie)
            self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))

    def dump_cookie(self):
        return self.cookie.dump() if self.cookie is not None else None

    def fetch(self, url, verifycert=True, method='GET', header=None, data=None, wait=5):
        """
        :param url: request URL
        :param verifycert: Certification check when using https, if False, skip that
        :param method: HTTP request method GET/POST/OPTION...
        :param header: Extra Header during request
        :param data: HTTP request parameters for GET/POST
        :param wait: Request wait time, default 5s
        :return: The page content requested.
            The difference from curl method is that, to help DOM extraction,
             if no content returned due to network issue, replace with Empty <html /> for lxml processing
        """
        result = self.curl(url, verifycert=verifycert, method=method, header=header, data=data, wait=wait)
        if result == '':
            logging.info('Request result is None, return EMPTY HTML ...')
            return '<html />'
        else:
            return result

    def curl(self, url, verifycert=True, method='GET', header=None, data=None, wait=5):
        """
        :param url: request URL
        :param verifycert: Certification check when using https, if False, skip that
        :param method: HTTP request method GET/POST/OPTION...
        :param header: Extra Header during request
        :param data: HTTP request parameters for GET/POST
        :param wait: Request wait time, default 5s
        :return: The page content requested. When network issue/HTTPS certification issue happened, returned ''
        """
        if not urlparse.urlparse(url).scheme:
            url = "http://" + url
        logger.debug('Requested %s URL: %s' % (method, url))

        if not self.cookie:
            logger.debug('Construct empty cookie ...')
            self.cookie = strcookiejar.StrCookieJar()
            self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))

        _headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android 4.1.1; zh-cn;  MI2 Build/JRO03L) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30 XiaoMi/MiuiBrowser/1.0',
            'Accept-Language': 'zh-cn,zh,en',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Charset': 'GB2312,utf-8',
            'Connection': 'Keep-Alive, TE',
        }
        if method.upper() == 'POST':
            _headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'

        if header and type(header) is dict:
            _headers.update(header)
        logger.debug('Construct HTTP headers:\n%s' % json.dumps(_headers, indent=4))

        if type(data) is not dict:
            data = {}

        if method.upper() == 'POST':
            data = urllib.urlencode(data).encode('utf-8')
            request = urllib2.Request(url=url, headers=_headers, data=data)
        else:
            if data:
                data = urllib.urlencode(data).encode('utf-8')
                url = '%s?%s' % (url, data)

            request = urllib2.Request(url=url, headers=_headers)

        response = None
        resp = None
        retry = False
        self._data = {}

        try:
            logger.info('Send out request ...')
            response = self.opener.open(request, timeout=wait)
            resp = response.read()
        except urllib2.URLError as e:
            error = e.reason
            if not verifycert and isinstance(error, ssl.SSLError) and error.reason == u'CERTIFICATE_VERIFY_FAILED':
                retry = True
            else:
                logger.error('Caught URLError, reason: %s', error)
                return ''
        except:
            logger.error('Caught urllib2 Error, maybe bad url? or website down? ...')
            return ''

        if retry:
            logger.info('Disable SSL Certification verify and retry the request ...')

            backup = ssl._create_default_https_context
            ssl._create_default_https_context = ssl._create_unverified_context
            try:
                response = self.opener.open(request, timeout=wait)
                resp = response.read()
            except:
                logger.error('Still no response without SSL Certificate verification ....')

                return ''
            finally:
                logger.debug('Restore the SSL context for the next time request ...')
                ssl._create_default_https_context = backup

        response.close()

        encoding = response.info().get('Content-Encoding')
        is_gzip = False
        if encoding:
            if 'gzip' in encoding.lower():
                is_gzip = True

        if is_gzip:
            r = zlib.decompress(resp, 16 + zlib.MAX_WBITS)
            logger.debug('Decompress the received packets ...')
        else:
            r = resp
        self._data['gzip'] = is_gzip

        try:
            ret = r.decode('utf-8')
        except UnicodeDecodeError:
            logger.warn('NOT Unicode, return what we got from server ...')
            ret = r

        self._data['code'] = response.getcode()
        self._data['url'] = response.geturl()
        self._data['headers'] = response.headers.dict

        logger.debug('Fetch Result for Request: %s\n%s' % (url, json.dumps(self._data, indent=4)))

        return ret
