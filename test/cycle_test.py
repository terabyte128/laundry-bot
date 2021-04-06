import unittest
import os
import tempfile

from flask_migrate import upgrade

from laundrybot import laundrybot
from laundrybot.models import Load, Machine, Roommate
from laundrybot.machines import MachineData


class TestMachineCycles(unittest.TestCase):
    def setUp(self):
        self.fd, self.filename = tempfile.mkstemp()
        config = {"SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.filename}"}

        self.app = laundrybot.create_app(**config)
        self.client = self.app.test_client()

        with self.app.app_context():
            upgrade(directory="laundrybot/migrations")

    def tearDown(self):
        os.close(self.fd)
        os.unlink(self.filename)

    def test_start_washer(self):
        """Should start washer cycle 1"""
        self.client.post("/api/update", data={"washer": 10, "dryer": 2})

        with self.app.app_context():
            load = Load.query.first()

            self.assertIsNotNone(load)
            self.assertIsNone(load.roommate)
            self.assertEqual(load.machine.id, MachineData.WASHER.value.id)
            self.assertEqual(load.cycle_number, 1)
            self.assertFalse(load.collected)

    def test_push_button_autostart_washer(self):
        """Should start washer cycle 0 and link with person"""
        self.client.post("/api/button", data={"name": "Sam"})

        with self.app.app_context():
            load = Load.query.first()

            self.assertIsNotNone(load)
            self.assertEqual(load.roommate.name, "Sam")
            self.assertEqual(load.machine.id, MachineData.WASHER.value.id)
            self.assertEqual(load.cycle_number, 0)
            self.assertFalse(load.collected)

    def test_push_button_then_start_washer(self):
        """Should start washer cycle 1 and link with person"""
        self.client.post("/api/button", data={"name": "Sam"})
        self.client.post(
            "/api/update",
            data={
                "washer": 10,
                "dryer": 2,
            },
        )

        with self.app.app_context():
            load = Load.query.first()

            self.assertIsNotNone(load)
            self.assertEqual(load.roommate.name, "Sam")
            self.assertEqual(load.machine.id, MachineData.WASHER.value.id)
            self.assertEqual(load.cycle_number, 1)
            self.assertFalse(load.collected)

    def test_start_washer_then_push_button(self):
        """Should start washer cycle 1 and link with person"""
        self.client.post(
            "/api/update",
            data={
                "washer": 10,
                "dryer": 2,
            },
        )
        self.client.post("/api/button", data={"name": "Sam"})

        with self.app.app_context():
            load = Load.query.first()

            self.assertIsNotNone(load)
            self.assertEqual(load.roommate.name, "Sam")
            self.assertEqual(load.machine.id, MachineData.WASHER.value.id)
            self.assertEqual(load.cycle_number, 1)
            self.assertFalse(load.collected)

    def test_start_dryer(self):
        """Should start dryer cycle 1"""
        self.client.post(
            "/api/update",
            data={
                "washer": 2,
                "dryer": 10,
            },
        )

        with self.app.app_context():
            load = Load.query.first()

            self.assertIsNotNone(load)
            self.assertIsNone(load.roommate)
            self.assertEqual(load.machine.id, MachineData.DRYER.value.id)
            self.assertEqual(load.cycle_number, 1)
            self.assertFalse(load.collected)

    def test_start_dryer_then_push_button(self):
        """Should start dryer cycle 1 and link with person"""
        self.client.post(
            "/api/update",
            data={
                "washer": 2,
                "dryer": 10,
            },
        )
        self.client.post("/api/button", data={"name": "Sam"})

        with self.app.app_context():
            load = Load.query.first()

            self.assertIsNotNone(load)
            self.assertEqual(load.roommate.name, "Sam")
            self.assertEqual(load.machine.id, MachineData.DRYER.value.id)
            self.assertEqual(load.cycle_number, 1)
            self.assertFalse(load.collected)

    def test_all_washer_cycles(self):
        """Should go through all washer cycles and mark end_time"""
        for i in [10, 2, 10, 2, 10, 2, 10]:
            self.client.post(
                "/api/update",
                data={
                    "washer": i,
                    "dryer": 2,
                },
            )

            # should not be done yet
            with self.app.app_context():
                load = Load.query.first()
                self.assertFalse(load.collected)
                self.assertIsNone(load.end_time)

        # should be done now
        self.client.post("/api/update", data={"washer": 2, "dryer": 2})

        with self.app.app_context():
            load = Load.query.first()
            self.assertFalse(load.collected)
            self.assertIsNotNone(load.end_time)

    def test_transfer_anonymous_load_washer_to_dryer(self):
        """Should transfer from washer to dryer"""

        # run through all washer cycles
        for i in [10, 2, 10, 2, 10, 2, 10, 2]:
            self.client.post(
                "/api/update",
                data={
                    "washer": i,
                    "dryer": 2,
                },
            )

        with self.app.app_context():
            load = Load.query.first()
            self.assertFalse(load.collected)
            self.assertIsNotNone(load.end_time)

        # start the dryer
        self.client.post(
            "/api/update",
            data={
                "washer": 2,
                "dryer": 10,
            },
        )

        with self.app.app_context():
            loads = Load.query.order_by(Load.start_time.asc())

            self.assertEqual(loads.count(), 2)

            washer_load = loads[0]
            dryer_load = loads[1]

            self.assertTrue(washer_load.collected)
            self.assertFalse(dryer_load.collected)

    def test_transfer_named_load_washer_to_dryer(self):
        """Should transfer named load from washer to dryer"""

        self.client.post("/api/button", data={"name": "Sam"})

        # run through all washer cycles
        for i in [10, 2, 10, 2, 10, 2, 10, 2]:
            self.client.post(
                "/api/update",
                data={
                    "washer": i,
                    "dryer": 2,
                },
            )

        with self.app.app_context():
            load = Load.query.first()
            self.assertFalse(load.collected)
            self.assertIsNotNone(load.end_time)
            self.assertEqual(load.roommate.name, "Sam")

        # start the dryer
        self.client.post(
            "/api/update",
            data={
                "washer": 2,
                "dryer": 10,
            },
        )

        with self.app.app_context():
            loads = Load.query.order_by(Load.start_time.asc())

            self.assertEqual(loads.count(), 2)

            washer_load = loads[0]
            dryer_load = loads[1]

            self.assertTrue(washer_load.collected)
            self.assertFalse(dryer_load.collected)
            self.assertEqual(dryer_load.roommate.name, "Sam")

    def test_collect_named_dryer_load(self):
        """Pushing the button again should mark the load collected"""

        # start the dryer
        self.client.post(
            "/api/update",
            data={
                "washer": 2,
                "dryer": 10,
            },
        )

        # push the button
        self.client.post("/api/button", data={"name": "Sam"})

        # end the dryer
        self.client.post(
            "/api/update",
            data={
                "washer": 2,
                "dryer": 2,
            },
        )

        with self.app.app_context():
            load = Load.query.first()

            self.assertFalse(load.collected)
            self.assertTrue(load.end_time)

            self.client.post("/api/button", data={"name": "Sam"})

            load = Load.query.first()

            self.assertTrue(load.collected)

        def test_multiple_loads_in_flight(self):
            # push the button
            self.client.post("/api/button", data={"name": "Sam"})

            # run through all washer cycles
            for i in [10, 2, 10, 2, 10, 2, 10, 2]:
                self.client.post(
                    "/api/update",
                    data={
                        "washer": i,
                        "dryer": 2,
                    },
                )

            with self.app.app_context():
                load = Load.query.first()
                self.assertFalse(load.collected)
                self.assertIsNotNone(load.end_time)
                self.assertEqual(load.roommate.name, "Sam")

            # start the dryer
            self.client.post(
                "/api/update",
                data={
                    "washer": 2,
                    "dryer": 10,
                },
            )

            with self.app.app_context():
                loads = Load.query.order_by(Load.start_time.asc())

                self.assertEqual(loads.count(), 2)

                washer_load = loads[0]
                dryer_load = loads[1]

                self.assertTrue(washer_load.collected)
                self.assertFalse(dryer_load.collected)
                self.assertEqual(dryer_load.roommate.name, "Sam")

            # person 2 pushes the button
            self.client.post("/api/button", data={"name": "Luke"})

            # person 2 runs through some of the washer cycles
            for i in [10, 2, 10, 2]:
                self.client.post(
                    "/api/update",
                    data={
                        "washer": i,
                        "dryer": 10,
                    },
                )

            with self.app.app_context():
                washer_load = Load.query.last()
                self.assertFalse(washer_load.collected)
                self.assertIsNone(washer_load.end_time)
                self.assertEqual(washer_load.roommate.name, "Luke")

                dryer_load = Load.query.first()
                self.assertFalse(dryer_load.collected)
                self.assertIsNone(dryer_load.end_time)
                self.assertEqual(dryer_load.roommate.name, "Sam")

            # person 2 runs through the rest of the washer cycles
            for i in [10, 2, 10, 2]:
                self.client.post(
                    "/api/update",
                    data={
                        "washer": i,
                        "dryer": 10,
                    },
                )

            with self.app.app_context():
                washer_load = Load.query.last()
                self.assertFalse(washer_load.collected)
                self.assertIsNotNone(washer_load.end_time)
                self.assertEqual(washer_load.roommate.name, "Luke")

                dryer_load = Load.query.first()
                self.assertFalse(dryer_load.collected)
                self.assertIsNone(dryer_load.end_time)
                self.assertEqual(dryer_load.roommate.name, "Sam")

            # person 1 finishes dryer
            self.client.post(
                "/api/update",
                data={
                    "washer": 2,
                    "dryer": 2,
                },
            )

            with self.app.app_context():
                washer_load = Load.query.last()
                self.assertFalse(washer_load.collected)
                self.assertIsNotNone(washer_load.end_time)
                self.assertEqual(washer_load.roommate.name, "Luke")

                dryer_load = Load.query.first()
                self.assertFalse(dryer_load.collected)
                self.assertIsNotNone(dryer_load.end_time)
                self.assertEqual(dryer_load.roommate.name, "Sam")

            # person 1 collects their dryer clothes
            self.client.post("/api/button", data={"name": "Sam"})

            with self.app.app_context():
                washer_load = Load.query.last()
                self.assertFalse(washer_load.collected)
                self.assertIsNotNone(washer_load.end_time)
                self.assertEqual(washer_load.roommate.name, "Luke")

                dryer_load = Load.query.first()
                self.assertTrue(dryer_load.collected)
                self.assertIsNotNone(dryer_load.end_time)
                self.assertEqual(dryer_load.roommate.name, "Sam")

            # person 2 transfers clothes to dryer and starts it
            self.client.post(
                "/api/update",
                data={
                    "washer": 2,
                    "dryer": 10,
                },
            )

            with self.app.app_context():
                dryer_load = Load.query.last()
                self.assertFalse(dryer_load.collected)
                self.assertIsNone(dryer_load.end_time)
                self.assertEqual(dryer_load.roommate.name, "Luke")

            # person 2 finishes dryer
            self.client.post(
                "/api/update",
                data={
                    "washer": 2,
                    "dryer": 2,
                },
            )

            with self.app.app_context():
                dryer_load = Load.query.last()
                self.assertFalse(dryer_load.collected)
                self.assertIsNotNone(dryer_load.end_time)
                self.assertEqual(dryer_load.roommate.name, "Luke")

            # person 2 collects clothing
            self.client.post("/api/button", data={"name": "Luke"})

            with self.app.app_context():
                dryer_load = Load.query.last()
                self.assertTrue(dryer_load.collected)
                self.assertIsNotNone(dryer_load.end_time)
                self.assertEqual(dryer_load.roommate.name, "Luke")

                for load in Load.query.all():
                    self.assertTrue(load.collected)
                    self.assertIsNotNone(load.end_time)
