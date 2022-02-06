#-*- coding: utf-8 -*-

import argparse
import hid
import usb.core
import usb.util

from singleton import Singleton

GP_NAME_ID_VENDOR = 'id_vendor'
GP_NAME_ID_PRODUCT = 'id_vendor'

GP_HID = 'hid'
GP_USB = 'usb'

GP_NAME_NAME = 'name'
GP_NAME_DEVICE = 'device'
GP_NAME_ENDPOINT = 'endpoint'
GP_NAME_ENDPOINT_ADDRESS = 'endpoint_address'
GP_NAME_LENGTH = 'length'
GP_VALUE_LENGTH_DEFAULT = 64
GP_NAME_GPV_PREVIOUS = 'gpv_previous'
GP_VALUE_GPV_PREVIOUS = ['0']
GP_VALUE_GPV_BASE = [128, 128, 0, 128, 128, 15, 0, 0]

GP_NAME_STICK_LEFT = 'stick_left'
GP_NAME_STICK_RIGHT = 'stick_right'
GP_NAME_BUTTON_LEFT = 'button_left'
GP_NAME_BUTTON_RIGHT = 'button_right'
GP_NAME_BUTTON_OTHER = 'button_other'

GP_HID_NAME_PATH = 'path'
GP_HID_NAME_VENDOR = 'vendor_id'
GP_HID_NAME_PRODUCT = 'product_id'
GP_USB_NAME_VENDOR = 'idVendor'
GP_USB_NAME_PRODUCT = 'idProduct'


def digitalize_xy(rv):
    def digitalize(xy):
        if 0 <= xy < 85:
            return 0
        elif 85 <= xy <= 170:
            return 128
        elif 170 < xy <= 255:
            return 255
        else:
            return -1
    drv = rv[:]
    drv[0] = digitalize(rv[0])
    drv[1] = digitalize(rv[1])
    drv[3] = digitalize(rv[3])
    drv[4] = digitalize(rv[4])

    return drv

def get_status_gamepad(name, rv):
    rd = {}
    rd[GP_NAME_NAME] = name
    rd[GP_NAME_STICK_LEFT] = [rv[0], rv[1]]
    rd[GP_NAME_STICK_RIGHT] = [rv[3], rv[4]]
    if bool(rv[5] & 0b00001000):
        rd[GP_NAME_BUTTON_LEFT] = -1
    else:
        rd[GP_NAME_BUTTON_LEFT] = rv[5] & 0b00000111
    rd[GP_NAME_BUTTON_RIGHT] = [
        bool(rv[5] & 0b00010000),
        bool(rv[5] & 0b00100000),
        bool(rv[5] & 0b01000000),
        bool(rv[5] & 0b10000000)
    ]
    rd[GP_NAME_BUTTON_OTHER] = [
        bool(rv[6] & 0b00000001),
        bool(rv[6] & 0b00000010),
        bool(rv[6] & 0b00000100),
        bool(rv[6] & 0b00001000),
        bool(rv[6] & 0b00010000),
        bool(rv[6] & 0b00100000),
        bool(rv[6] & 0b01000000),
        bool(rv[6] & 0b10000000)
    ]

    return rd


class GamepadHID(Singleton):
    def __init__(self, *args, **kwargs):
        super(GamepadHID, self).__init__()
        if GP_NAME_ID_VENDOR not in kwargs or GP_NAME_ID_PRODUCT not in kwargs:
            print(f'There is not {GP_NAME_ID_VENDOR} or {GP_NAME_ID_PRODUCT}')
            exit()
        self.status_base = GP_VALUE_GPV_BASE
        if not hasattr(self, 'pads'):
            self.pads = []
        self.append_pad(*args, **kwargs)

    def append_pad(self, *args, **kwargs):
        pad = kwargs.copy()
        if GP_NAME_LENGTH not in pad:
            pad[GP_NAME_LENGTH] = GP_VALUE_LENGTH_DEFAULT
        if GP_NAME_GPV_PREVIOUS not in pad:
            pad[GP_NAME_GPV_PREVIOUS] = GP_VALUE_GPV_PREVIOUS
        device = hid.device()
        device.open_path(pad[GP_HID_NAME_PATH])
        device.set_nonblocking(True)
        pad[GP_NAME_DEVICE] = device
        self.pads.append(pad)

    def read_pads(self):
        for pad in self.pads:
            try:
                rv = pad[GP_NAME_DEVICE].read(pad[GP_NAME_LENGTH])
                drv = []
                if rv:
                    drv = digitalize_xy(rv)
                if drv and pad[GP_NAME_GPV_PREVIOUS] != drv:
                    pad[GP_NAME_GPV_PREVIOUS] = drv
                    status = get_status_gamepad(pad[GP_NAME_NAME], drv)
                    yield status
            except Exception as e:
                print(f'{e}: {pad}')
                continue


class GamepadUSB(Singleton):
    def __init__(self, *args, **kwargs):
        super(GamepadUSB, self).__init__()
        self.status_base = GP_VALUE_GPV_BASE
        if not hasattr(self, 'pads'):
            self.pads = []
        self.append_pad(*args, **kwargs)

    def append_pad(self, *args, **kwargs):
        pad = kwargs.copy()
        if GP_NAME_LENGTH not in pad:
            pad[GP_NAME_LENGTH] = GP_VALUE_LENGTH_DEFAULT
        if GP_NAME_GPV_PREVIOUS not in pad:
            pad[GP_NAME_GPV_PREVIOUS] = GP_VALUE_GPV_PREVIOUS

        pad[GP_NAME_ENDPOINT] = pad[GP_NAME_DEVICE][0].interfaces()[0].endpoints()[0]
        pad[GP_NAME_DEVICE].reset()
        pad[GP_NAME_DEVICE].set_configuration()
        pad[GP_NAME_ENDPOINT_ADDRESS] = pad[GP_NAME_ENDPOINT].bEndpointAddress
        self.pads.append(pad)

    def read_pads(self):
        for pad in self.pads:
            try:
                rv = pad[GP_NAME_DEVICE].read(pad[GP_NAME_ENDPOINT_ADDRESS], pad[GP_NAME_LENGTH])
                drv = []
                if rv:
                    drv = digitalize_xy(rv)
                if drv and pad[GP_NAME_GPV_PREVIOUS] != drv:
                    pad[GP_NAME_GPV_PREVIOUS] = drv
                    status = get_status_gamepad(pad[GP_NAME_NAME], drv)
                    yield status
            except Exception as e:
                print(f'{e}: {pad}')
                continue

# python gamepad.py --use hid --names player1 player2 --vendor 121 --product 6
# python gamepad.py --use usb --names player1 player2 --vendor 121 --product 6
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Read Gamepad')
    parser.add_argument('--use', choices=[GP_HID, GP_USB], default='usb', help='Select hid or usb')
    parser.add_argument('--names', nargs='*', default=['player1', 'player2'], help='Gamepad name list')
    parser.add_argument('--vendor', default='121', help='ID vendor')
    parser.add_argument('--product', default='6', help='ID product')
    args = parser.parse_args()
    print(args.use)
    print(args.names.pop(0))
    print(args.names.pop(0))
    print(args.vendor)
    print(args.product)

    if (args.use == GP_HID):
        for device in hid.enumerate(vendor_id=int(args.vendor), product_id=int(args.product)):
        # for device in hid.enumerate(vendor_id=121, product_id=6):
        # {'path': b'\\\\?\\hid#vid_0079&pid_0006#6&123605f&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}', 'vendor_id': 121, 'product_id': 6, 'serial_number': '', 'release_number': 263, 'manufacturer_string': 'Microntek             ', 'product_string': 'USB Joystick          ', 'usage_page': 1, 'usage': 4, 'interface_number': -1}
        # {'path': b'\\\\?\\hid#vid_0079&pid_0006#6&395290e7&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}', 'vendor_id': 121, 'product_id': 6, 'serial_number': '', 'release_number': 263, 'manufacturer_string': 'Microntek             ', 'product_string': 'USB Joystick          ', 'usage_page': 1, 'usage': 4, 'interface_number': -1}
            gp = GamepadHID(name=args.names.pop(0), path=device[GP_HID_NAME_PATH])

    elif args.use == GP_USB:
        for device in usb.core.find(find_all=True, idVendor=int(args.vendor), idProduct=int(args.product)):
            gp = GamepadUSB(name=args.names.pop(0), device=device)

    try:
        gp
    except Exception as e:
        print(f'Cannot find any gamepad')
        raise SystemExit

    if gp is not None:
        print(f'gp.pads: {gp.pads}')
        while True:
            for status in gp.read_pads():
                print(f'====== {status}')
