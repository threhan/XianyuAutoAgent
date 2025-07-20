import unittest
import os
import json
from unittest.mock import patch, MagicMock
from XianyuApis import XianyuApis

class TestXianyuApis(unittest.TestCase):

    def setUp(self):
        config = {
            "api_endpoints": {
                "get_token_url": "https://h5api.m.goofish.com/h5/mtop.taobao.idlemessage.pc.login.token/1.0/",
                "get_item_info_url": "https://h5api.m.goofish.com/h5/mtop.taobao.idle.pc.detail/1.0/",
                "has_login_url": "https://passport.goofish.com/newlogin/hasLogin.do",
                "appKey": "34839810",
                "tokenAppKey": "444e9908a51d1cb236a27862abc769c9"
            },
            "common_api_params": {
                "jsv": "2.7.2",
                "v": "1.0",
                "type": "originaljson",
                "accountSite": "xianyu",
                "dataType": "json",
                "timeout": "20000",
                "sessionOption": "AutoLoginOnly",
                "spm_cnt": "a21ybx.im.0.0"
            }
        }
        self.api = XianyuApis()

    

    @patch('requests.Session.post')
    def test_get_token_success(self, mock_post):
        # Mock the response from the API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ret": ["SUCCESS::调用成功"],
            "data": {"accessToken": "test_token"}
        }
        mock_post.return_value = mock_response

        # Call the method
        result = self.api.get_token("test_device_id")

        # Assert the result
        self.assertEqual(result['data']['accessToken'], "test_token")

    @patch('requests.Session.post')
    def test_get_item_info_success(self, mock_post):
        # Mock the response from the API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ret": ["SUCCESS::调用成功"],
            "data": {"itemDO": {"title": "test_item"}}
        }
        mock_post.return_value = mock_response

        # Call the method
        result = self.api.get_item_info("test_item_id")

        # Assert the result
        self.assertEqual(result['data']['itemDO']['title'], "test_item")

if __name__ == '__main__':
    unittest.main()
