import json
import logging.config
import sys

from com.Phoenixcontact.REST.RESTException import *
from com.Phoenixcontact.REST.RESTHttpClient import *


class DataGroup(object):

    @staticmethod
    def _RegisterGroup(self, variableNames, pathPrefix=RestConstant.PATHPREFIX):
        if self.accessToken == None:
            return

        _payload = {
            'pathPrefix': pathPrefix,
            'paths': variableNames
        }
        _status_code, _hearders, _text = RESTHttpClient.invokeAPI(httpMethod=RestConstant.POST,
                                                                  function_uri=RestConstant.REGISTER_GROUP_URI,
                                                                  clientInfo=self,
                                                                  payload=json.dumps(_payload))
        if _status_code == 201:  # Creat success
            _response = json.loads(_text)
            if _response.get('variables'):
                # return ReadGroup(groupID=_response.get('id'), vars=_response.get('variables'), clientInfo=clientInfo)
                logging.info('Group ID : {}'.format(_response.get('id')))
                return _response.get('id'), _response.get('variables')
        elif _status_code == 404:  # 变量名不正确
            _response = json.loads(_text)
            _reason = _response.get('error').get('details')[0].get('reason')
            logging.error(str(_reason))
            raise RESTException(_reason)
        elif _status_code == 401:  # 令牌不正确
            self.accessToken = None
            _reason = _hearders.get('WWW-Authenticate')
            logging.error(str(_reason))
            raise RESTException(_reason)  # Bearer realm="pxcapi", error="invalid_token"

    @staticmethod
    def _ReadGroupValues(ReadGroup):
        if ReadGroup.groupID == None or ReadGroup.clientInfo.accessToken == None:
            return
        _url = RestConstant.READ_GROUP_URI + ReadGroup.groupID
        _status_code, _hearders, _text = RESTHttpClient.invokeAPI(httpMethod=RestConstant.GET,
                                                                  function_uri=_url,
                                                                  clientInfo=ReadGroup.clientInfo,
                                                                  payload=None)
        if _status_code == 200:
            _response = json.loads(_text)
            if _response.get('id') == ReadGroup.groupID:
                ReadGroup.valves = _response.get('variables')
                Result = dict()
                for _item in ReadGroup.valves:
                    Result[_item['path']] = _item['value']
                return Result
        elif _status_code == 404:  # groupID不正确
            ReadGroup.groupID = None
            _response = json.loads(_text)
            _reason = _response.get('error').get('details')[0].get('reason')
            logging.error(_reason)
            raise RESTException(_reason)
        elif _status_code == 401:  # 令牌不正确loads
            ReadGroup.clientInfo.accessToken = None
            _reason = _hearders.get('WWW-Authenticate')
            logging.error(_reason)
            raise RESTException(_reason)  # Bearer realm="pxcapi", error="invalid_token"
        elif _status_code == 400:  # 指令不正确
            _response = json.loads(_text)
            _reason = _response.get('error').get('details')[0].get('reason')
            logging.error(_reason)
            raise RESTException(_reason)

    # @staticmethod
    # def Unregister(GroupInfo):
    #     if GroupInfo.groupID == None:
    #         return
    #     _url = RestConstant.UNREGISTER_GROUP_URI + GroupInfo.groupID
    #
    #     _status_code, _hearders, _text = RESTHttpClient.invokeAPI(httpMethod=RestConstant.DELETE,
    #                                                               authUri=_url,
    #                                                               ClientInfo=GroupInfo.clientInfo,
    #                                                               payload=None)
    #     pass

    @staticmethod
    def _ReportGroups(self):
        if self.accessToken == None:
            return
        _status_code, _hearders, _text = RESTHttpClient.invokeAPI(httpMethod=RestConstant.GET,
                                                                  function_uri=RestConstant.REPORT_GROUP_URI,
                                                                  clientInfo=self,
                                                                  payload=None)
        if _status_code == 200:
            _response = json.loads(_text).get('groups')
            self.groupReportResult = _response
            return self.groupReportResult
        elif _status_code == 401:  # 令牌不正确loads
            self.accessToken = None
            _reason = _hearders.get('WWW-Authenticate')
            logging.error(_reason)
            raise RESTException(_reason)  # Bearer realm="pxcapi", error="invalid_token"
        elif _status_code == 400:  # 指令不正确
            _response = json.loads(_text)
            _reason = _response.get('error').get('details')[0].get('reason')
            logging.error(_reason)
            raise RESTException(_reason)


class ReadGroup(object):
    def __init__(self, vars, Parent, groupID=None, varName=None, prefix=None):
        self.groupID = groupID
        self.vars = vars
        self.valves = None
        self.clientInfo = Parent
        self._Parent = Parent
        self.__reConnectCount = 0
        self.__reFreshCount = 0
        self._Results = {}
        self._varName_BACKUP = varName
        self._prefix_BACKUP = prefix

    @property
    def results(self):
        self._Read()
        return self._Results

    def __getitem__(self, item):
        self._Read()
        return self._Results.get(item, None)

    def __str__(self):
        return 'groupID : ' + str(self.groupID) + ' | vars : ' + str(self.vars) + ' | valves : ' + str(
            self.valves) + " | " + str(self.clientInfo)

    def checkMemberType(self):
        _ResultDict = dict()
        for _item in self.vars:
            _varName = _item.get('path')
            _ResultDict[_varName] = _item.get('type')
        return _ResultDict

    def _Read(self):
        while True:
            if self._Parent.accessToken == None:
                logging.error("Impossible to call " + (sys._getframe().f_code.co_name) + " without token")
                self._Parent.Connect()
            try:
                Result = DataGroup._ReadGroupValues(self)
                self.__reConnectCount = 0
                self.__reFreshCount = 0
                self._Results = Result
                return self._Results
            except RESTException as E:
                if 'invalid_token' in E.message and self.__reConnectCount < 2:
                    self.__reConnectCount += 1
                    self._Parent._reConnect()
                if 'invalidGroupID' in E.message and self.__reFreshCount < 2:
                    logging.info('Trying to refresh group ID')
                    self.__reFreshCount += 1
                    self.refreshID()
                else:
                    raise E

    def refreshID(self):
        __newID, __NewRes = self._Parent.registerReadGroups(self._varName_BACKUP, self._prefix_BACKUP, _object=False)
        self.groupID = __newID