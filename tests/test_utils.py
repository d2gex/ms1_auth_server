from authorization_server import utils


def test_init_class():

    @utils.init_class
    class Stub:

        x = None

        @classmethod
        def init(cls):
            cls.x = 10

    assert Stub.x == 10
