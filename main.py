from PyQt5 import QtWidgets
from PyQt5.QtGui import QTextCursor
import socket
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from mystatus import Ui_MainWindow
import utils
from time import sleep
import datetime


class RequestThread(QThread):
    """
    请求得到各节点数据
    """
    BatteryLevel = None
    UpdateSignal = pyqtSignal(str, dict)
    UpdateBatteryLevel = pyqtSignal(str)

    def __init__(self):
        super(RequestThread, self).__init__()
        self.nodes = list()
        self.StopFlag = False

    # 添加节点
    def AddNode(self, NodeName: str):
        self.nodes.append(NodeName)
    
    def AddBatteryLevel(self, BatteryLevel: str):
        self.BatteryLevel.append(BatteryLevel)
        
    def run(self):
        self.UpdateBatteryLevel.emit(self.BatteryLevel)
        while not self.StopFlag:
            for NodeName in self.nodes:
                # 请求得到一个节点的数据，就提交一次
                self.UpdateSignal.emit(NodeName,
                                       utils.get_node_information(NodeName))
                # 请求每个节点数据并发送后的延时
                sleep(2)

    # 提供外部接口来设置 StopFlag 状态,节点离线调用该方法来停止数据提交
    def stop(self):
        self.StopFlag = True


class Sensor:
    """
    连接远程服务器，即节点
    """
    @staticmethod
    def check_sensor_ip(ip_address, port, timeout=0.1):
        # 创建套接字并设置超时时间
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(timeout)

        # 记录连接状态
        is_connection_successful = False

        try:
            # 尝试连接远程服务器
            client_socket.connect((ip_address, port))
            is_connection_successful = True  # 标记连接成功
        except (ConnectionRefusedError, socket.timeout):
            # 连接被拒绝或超时，标记连接失败
            is_connection_successful = False
        finally:
            # 在完成操作后关闭客户端套接字
            client_socket.close()

        # 根据连接状态返回相应的布尔值
        return is_connection_successful


# 设置全局变量来记录三个节点在线与否
global_sensor1 = False
global_sensor2 = False
global_sensor3 = False


class UsingWindow(QMainWindow, Ui_MainWindow, QTabWidget):
    """
    继承window的布局类，在此处编写逻辑代码
    """
    value_changed = pyqtSignal(int)  # 声明名为 value_changed 的信号

    def __init__(self):
        super(UsingWindow, self).__init__()
        self.setupUi(self)
        self.list_widget = QListWidget()
        self.value_changed.connect(self.update_list_widget)
        self.check_node_online_status()

        # 所有传感器的参数信息，以字典方式存在
        self.nodes_sensor_parameters = dict()

        # 初始化一个持续请求传感器参数的线程
        self.request_thread = RequestThread()
        # 每次得到请求数据，就将数据交由self.process_request_signal处理
        self.request_thread.UpdateSignal.connect(self.process_request_signal)
        self.request_thread.start()  # 启动持续请求传感器参数的线程

        # 添加节点
        NodeName = ["CarbonSign", "SulfurSign", "NoiseSign"]

        # 传感器各种数据的相应要求
        self.sensor_parameters_requirements = \
            {
                "二氧化碳": lambda x: 0 <= x < 700,
                "二氧化硫": lambda x: 0 <= x < 1,
                "噪音": lambda x: 0 <= x < 50,
            }


    def update_list_widget(self, text):
        self.list_widget.addItem(text)

    def AddNode(self, NodeName: str):
        self.request_thread.AddNode(NodeName)  # 持续请求传感器参数的线程节点列表

    def process_request_signal(self, NodeName, node_sensor_parameters):
        """
                处理请求得到的字典
        """
        global_sensor = 0
        # 如果节点在线，检查各个传感器参数是否满足要求
        if NodeName == "CarbonSign":
            global_sensor = NodeName[0]
        elif NodeName == "SulfurSign":
            global_sensor = NodeName[1]
        elif NodeName == "NoiseSign":
            global_sensor = NodeName[2]
        if global_sensor:
            self.check_if_parameters_required(NodeName, node_sensor_parameters)
        else:
            self.CarbonStatus1.appendPlainText(f'节点不在线，请重新连接')

    def check_if_parameters_required(self, NodeName, node_sensor_parameters):
        """
          检查传感器参数是否满足要求，若不满足要求，更新window log
        """
        cursor = QTextEdit().textCursor()
        # 创建存储出错的节点列表
        wrong_parameters = list()

        # 把值赋值给sensor_parameters
        sensor_parameters = node_sensor_parameters["sensor_parameters"]
        # 键赋值给sensor_name,值赋值给parameter
        for sensor_name, parameter in sensor_parameters.items():
            # 判断测得数据是否符合标准
            if not self.sensor_parameters_requirements[sensor_name](parameter):
                wrong_parameters.append(sensor_name)
        # 如果错误参数列表不为空，打印错误日志
        if len(wrong_parameters) != 0:
            if NodeName == "CarbonSign":
                # 获取 CarbonStatus1 对象
                lineEdit = self.findChild(QtWidgets.QPlainTextEdit, "CarbonStatus1")
                # 将焦点设置为 CarbonStatus1
                lineEdit.setFocus()
                # 获取 CarbonStatus1 的 QTextCursor
                cursor = lineEdit.textCursor()
                # 直接移到行首位置
                cursor.movePosition(QTextCursor.Start)
                text = "出现问题"
                self.CarbonStatus1.appendPlainText(f'{NodeName}{node_sensor_parameters}')
                cursor.insertHtml(f"<span style='color: red; font-weight: bold'>{text}</span>")

            elif NodeName == "SulfurSign":
                # 获取 SulfurStatus2 对象
                lineEdit = self.findChild(QtWidgets.QPlainTextEdit, "SulfurStatus2")
                # 将焦点设置为 SulfurStatus2
                lineEdit.setFocus()
                # 获取 SulfurStatus2 的 QTextCursor
                cursor = lineEdit.textCursor()
                # 直接移到行首位置
                cursor.movePosition(QTextCursor.Start)
                text = "出现问题"
                self.SulfurStatus2.appendPlainText(f'{NodeName}{node_sensor_parameters}')
                cursor.insertHtml(f"<span style='color: red; font-weight: bold'>{text}</span>")

            elif NodeName == "NoiseSign":
                # 获取 NoiseLabel3 对象
                lineEdit = self.findChild(QtWidgets.QPlainTextEdit, "NoiseLabel3")
                # 将焦点设置为 NoiseLabel3
                lineEdit.setFocus()
                # 获取 NoiseLabel3 的 QTextCursor
                cursor = lineEdit.textCursor()
                # 直接移到行首位置
                cursor.movePosition(QTextCursor.Start)
                text = "出现问题"
                self.NoiseLabel3.appendPlainText(f'{NodeName}{node_sensor_parameters}')
                cursor.insertHtml(f"<span style='color: red; font-weight: bold'>{text}</span>")

        # 错误列表为空，正常输出数据
        else:
            if NodeName == "CarbonSign":
                self.CarbonStatus1.appendPlainText(f'{NodeName}{node_sensor_parameters}')
            elif NodeName == "SulfurSign":
                self.SulfurStatus2.appendPlainText(f'{NodeName}{node_sensor_parameters}')
            elif NodeName == "NoiseSign":
                self.NoiseLabel3.appendPlainText(f'{NodeName}{node_sensor_parameters}')

    def check_node_online_status(self):
        """
            检查在线状态是否改变，若改变，更新window log
        """
        # 获取当前时间
        current_time = datetime.datetime.now()

        # 三个传感器的IP地址
        sensor1_ip = '192.168.1.101'
        sensor2_ip = '192.168.1.102'
        sensor3_ip = '192.168.1.103'
        # 端口号
        PORT = 8000

        # 显示三个节点的在线掉线时间及状态
        self.status_2.append(current_time.strftime("%Y-%m-%d %H:%M:%S"))

        # 节点1
        if Sensor.check_sensor_ip(sensor1_ip, PORT):
            global global_sensor1
            global_sensor1 = True
            self.status.append('<font color="green">节点1连接</font>')
            self.status_2.append(f'<font color="green">节点1连接</font>')
        else:
            global_sensor1 = False
            self.status.append('<font color="red">节点1未连接</font>')
            self.status_2.append(f'<font color="red">节点1断开连接</font>')
            RequestThread.stop(self)
        # 节点2
        if Sensor.check_sensor_ip(sensor2_ip, PORT):
            global global_sensor2
            global_sensor2 = True
            self.status.append('<font color="green">节点2连接</font>')
            self.status_2.append(f'<font color="green">节点2连接</font>')
        else:
            global_sensor2 = False
            self.status.append('<font color="red">节点2未连接</font>')
            self.status_2.append(f'<font color="red">节点2断开连接</font>')
            RequestThread.stop(self)
        # 节点3
        if Sensor.check_sensor_ip(sensor3_ip, PORT):
            global global_sensor3
            global_sensor3 = True
            self.status.append('<font color="green">节点2连接</font>')
            self.status_2.append(f'<font color="green">节点3连接</font>')
        else:
            global_sensor3 = False
            self.status.append('<font color="red">节点3未连接</font>')
            self.status_2.append(f'<font color="red">节点3断开连接</font>')
            RequestThread.stop(self)


if __name__ == "__main__":
    app = QApplication([])
    win = UsingWindow()
    win.show()
    app.exec_()

