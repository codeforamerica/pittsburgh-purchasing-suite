# -*- coding: utf-8 -*-

from purchasing.database import db
from purchasing.data.models import Stage, StageProperty, ContractBase
from purchasing.data.stages import (
    create_new_stage, update_stage, update_stage_property,
    delete_stage, get_all_stages
)

from purchasing_test.unit.test_base import BaseTestCase
from purchasing_test.unit.util import (
    insert_a_stage, get_a_stage_property, insert_a_contract
)

class StageTest(BaseTestCase):
    def test_create_new_stage(self):
        # test standard stage w/no properties
        stage_data = dict(
            name='test'
        )

        stage = create_new_stage(stage_data)
        self.assertEquals(Stage.query.count(), 1)
        self.assertEquals(Stage.query.first().name, stage.name)

        # test stage with properties
        stage_data_props = dict(
            name='test2',
            properties=[
                dict(key='foo', value='bar'),
                dict(key='baz', value='qux')
            ]
        )

        stage_props = create_new_stage(stage_data_props)
        self.assertEquals(Stage.query.count(), 2)
        self.assertEquals(StageProperty.query.count(), 2)
        self.assertEquals(Stage.query.all()[-1].name, stage_props.name)

    def test_update_stage(self):
        stage = insert_a_stage()

        self.assertEquals(
            Stage.query.first().name,
            stage.name
        )

        update_stage(stage.id, {'name': 'new name'})

        self.assertEquals(
            Stage.query.first().name,
            'new name'
        )

    def test_update_contract_property(self):
        property = get_a_stage_property()

        update_stage_property(property.id, {'value': 'foo2'})

        self.assertEquals(
            StageProperty.query.get(property.id).value, 'foo2'
        )

    def test_delete_contract(self):
        stage = insert_a_stage()

        self.assertEquals(Stage.query.count(), 1)
        self.assertEquals(StageProperty.query.count(), 2)

        # deleting a stage should delete the stage and its props
        delete_stage(stage.id)

        self.assertEquals(Stage.query.count(), 0)
        self.assertEquals(StageProperty.query.count(), 0)

        # it should not delete any associated contracts
        stage = insert_a_stage()
        contract = insert_a_contract()

        contract.current_stage_id = stage.id
        db.session.commit()

        self.assertEquals(
            ContractBase.query.first().current_stage.id,
            stage.id
        )

        delete_stage(stage.id)

        self.assertEquals(
            ContractBase.query.first().current_stage,
            None
        )

    def test_get_stages(self):
        insert_a_stage()
        insert_a_stage()
        insert_a_stage()

        self.assertEquals(
            len(get_all_stages()), 3
        )
