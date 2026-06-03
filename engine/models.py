from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProcessBlock:
    id: int
    type: str
    x: float
    y: float
    process_time_per_ea: float = 30.0
    concurrent_capacity: int = 1
    product_name: str = "제품"
    material_name: str = "원자재"
    input_quantity: int = 10
    input_time: float = 0.0
    transport_capacity: int = 1
    transport_time: float = 1.0
    custom_name: str = ""
    width: int = 150
    height: int = 80


@dataclass
class ProcessConnection:
    id: int
    from_block: int
    to_block: int


@dataclass
class Operator:
    id: int
    name: str
    x: float
    y: float
    qualified_process_types: set[str] = field(default_factory=set)
    width: int = 130
    height: int = 64


@dataclass
class OperatorAssignment:
    id: int
    operator_id: int
    block_id: int


UNIVERSAL_OPERATOR_BLOCK_TYPES = {"INPUT", "HOIST", "FREE", "WORK_WAITING"}


def operator_can_handle_block(operator: Operator, block: ProcessBlock) -> bool:
    return (
        block.type in UNIVERSAL_OPERATOR_BLOCK_TYPES
        or block.type in operator.qualified_process_types
    )


@dataclass
class Scenario:
    blocks: list[ProcessBlock] = field(default_factory=list)
    connections: list[ProcessConnection] = field(default_factory=list)
    operators: list[Operator] = field(default_factory=list)
    operator_assignments: list[OperatorAssignment] = field(default_factory=list)

    def next_block_id(self) -> int:
        if not self.blocks:
            return 1
        return max(block.id for block in self.blocks) + 1

    def next_connection_id(self) -> int:
        if not self.connections:
            return 1
        return max(connection.id for connection in self.connections) + 1

    def next_operator_id(self) -> int:
        if not self.operators:
            return 1
        return max(operator.id for operator in self.operators) + 1

    def next_operator_assignment_id(self) -> int:
        if not self.operator_assignments:
            return 1
        return max(assignment.id for assignment in self.operator_assignments) + 1

    def add_block(
        self,
        block_type: str,
        x: float,
        y: float,
        process_time_per_ea: float = 30.0,
        concurrent_capacity: int = 1,
        product_name: str = "제품",
        material_name: str = "원자재",
        input_quantity: int = 10,
        input_time: float = 0.0,
        transport_capacity: int = 1,
        transport_time: float = 1.0,
        custom_name: str = "",
        block_id: int | None = None,
    ) -> ProcessBlock:
        block = ProcessBlock(
            id=block_id if block_id is not None else self.next_block_id(),
            type=block_type,
            x=x,
            y=y,
            process_time_per_ea=process_time_per_ea,
            concurrent_capacity=concurrent_capacity,
            product_name=product_name,
            material_name=material_name,
            input_quantity=input_quantity,
            input_time=input_time,
            transport_capacity=transport_capacity,
            transport_time=transport_time,
            custom_name=custom_name,
        )
        self.blocks.append(block)
        return block

    def delete_block(self, block_id: int) -> None:
        self.blocks = [block for block in self.blocks if block.id != block_id]
        self.connections = [
            connection
            for connection in self.connections
            if connection.from_block != block_id and connection.to_block != block_id
        ]
        self.operator_assignments = [
            assignment
            for assignment in self.operator_assignments
            if assignment.block_id != block_id
        ]

    def add_connection(
        self,
        from_block: int,
        to_block: int,
        connection_id: int | None = None,
    ) -> ProcessConnection:
        if from_block == to_block:
            raise ValueError("같은 블록끼리는 연결할 수 없습니다.")

        block_by_id = {block.id: block for block in self.blocks}
        if from_block not in block_by_id or to_block not in block_by_id:
            raise ValueError("연결하려는 블록이 시나리오에 있어야 합니다.")

        if block_by_id[to_block].type == "INPUT":
            raise ValueError("원자재 투입 블록으로 들어가는 연결은 만들 수 없습니다.")

        duplicate = any(
            connection.from_block == from_block and connection.to_block == to_block
            for connection in self.connections
        )
        if duplicate:
            raise ValueError("이미 존재하는 연결입니다.")

        if self._would_create_cycle(from_block, to_block):
            raise ValueError("순환 흐름은 지원하지 않습니다.")

        connection = ProcessConnection(
            id=connection_id if connection_id is not None else self.next_connection_id(),
            from_block=from_block,
            to_block=to_block,
        )
        self.connections.append(connection)
        return connection

    def delete_connection(self, connection_id: int) -> None:
        self.connections = [
            connection for connection in self.connections if connection.id != connection_id
        ]

    def add_operator(
        self,
        name: str,
        x: float,
        y: float,
        qualified_process_types: set[str] | list[str] | tuple[str, ...] | None = None,
        operator_id: int | None = None,
    ) -> Operator:
        if not name.strip():
            raise ValueError("Operator name is required.")

        operator = Operator(
            id=operator_id if operator_id is not None else self.next_operator_id(),
            name=name.strip(),
            x=x,
            y=y,
            qualified_process_types=set(qualified_process_types or ()),
        )
        self.operators.append(operator)
        return operator

    def delete_operator(self, operator_id: int) -> None:
        self.operators = [
            operator for operator in self.operators if operator.id != operator_id
        ]
        self.operator_assignments = [
            assignment
            for assignment in self.operator_assignments
            if assignment.operator_id != operator_id
        ]

    def add_operator_assignment(
        self,
        operator_id: int,
        block_id: int,
        assignment_id: int | None = None,
    ) -> OperatorAssignment:
        operator = self.operator_by_id(operator_id)
        block = self.block_by_id(block_id)

        if operator is None:
            raise ValueError("Operator does not exist in this scenario.")
        if block is None:
            raise ValueError("Process block does not exist in this scenario.")

        duplicate = any(
            assignment.operator_id == operator_id and assignment.block_id == block_id
            for assignment in self.operator_assignments
        )
        if duplicate:
            raise ValueError("This operator assignment already exists.")

        already_assigned = any(
            assignment.block_id == block_id
            for assignment in self.operator_assignments
        )
        if already_assigned:
            raise ValueError("This process block already has an assigned operator.")

        if not operator_can_handle_block(operator, block):
            raise ValueError("Operator is not qualified for this process type.")

        assignment = OperatorAssignment(
            id=assignment_id
            if assignment_id is not None
            else self.next_operator_assignment_id(),
            operator_id=operator_id,
            block_id=block_id,
        )
        self.operator_assignments.append(assignment)
        return assignment

    def delete_operator_assignment(self, assignment_id: int) -> None:
        self.operator_assignments = [
            assignment
            for assignment in self.operator_assignments
            if assignment.id != assignment_id
        ]

    def block_by_id(self, block_id: int) -> ProcessBlock | None:
        return next((block for block in self.blocks if block.id == block_id), None)

    def operator_by_id(self, operator_id: int) -> Operator | None:
        return next(
            (operator for operator in self.operators if operator.id == operator_id),
            None,
        )

    def _would_create_cycle(self, from_block: int, to_block: int) -> bool:
        stack = [to_block]
        visited: set[int] = set()

        while stack:
            current = stack.pop()
            if current == from_block:
                return True
            if current in visited:
                continue
            visited.add(current)

            stack.extend(
                connection.to_block
                for connection in self.connections
                if connection.from_block == current
            )

        return False
