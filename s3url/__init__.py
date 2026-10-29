import logging
from os.path import split
from typing import Optional
from urllib.parse import ParseResult, urlparse


class S3Url:
    """Class to parse S3 URLs."""

    logger: logging.Logger
    _parsed: ParseResult

    def __init__(self, url: Optional[str] = None, **kwargs: str):
        """Constructor.
        :param str url: An S3 URL
        :param str bucket: An S3 Bucket
        :param str prefix: An S3 Key Prefix
        :param str key: An S3 Key with or without a Prefix
        """

        self.logger = logging.getLogger('s3url-logger')

        bucket = kwargs.get('bucket', '')
        prefix = kwargs.get('prefix', '')
        key = kwargs.get('key', '')

        if url:
            self._parsed = urlparse(url, allow_fragments=False)
        elif prefix:
            self._parsed = urlparse(f's3://{bucket}/{prefix}/{key}', allow_fragments=False)
        else:
            self._parsed = urlparse(f's3://{bucket}/{key}', allow_fragments=False)

    @property
    def bucket(self) -> str:
        """Bucket Property.
        :rtype: str
        :return: the Bucket component of the URL
        """
        return self._parsed.netloc

    @property
    def key(self) -> str:
        """Key Property.
        :rtype: str
        :return:: the Key component of the URL
        """
        if self._parsed.query:
            return self._parsed.path.lstrip('/') + '?' + self._parsed.query
        return self._parsed.path.lstrip('/')

    @property
    def prefix(self) -> str:
        """Prefix Property.
        :rtype: str
        :return:: the Prefix component of the URL
        """
        return split(self._parsed.path.lstrip('/'))[0]

    @property
    def file(self) -> str:
        """File Property.
        :rtype: str
        :return:: the File name component of the URL
        """

        return split(self._parsed.path)[1]


    @property
    def url(self):
        """URL Property.
        :rtype: str
        :return: the complete URL
        """
        return self._parsed.geturl()


    @property
    def arn(self) -> str:
        """
        AWS Global Bucket Arn
        :rtype: str
        :return: AWS ARN
        """
        return 'arn:aws:s3:::' + self.bucket
