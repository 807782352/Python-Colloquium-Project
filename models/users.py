import hashlib


class User:
    def __init__(
        self,
        user_id,
        name,
        group_size,
        preferred_environment,
        budget,
        period,
        password_hash=None,
    ):
        self._user_id = (
            user_id.lower().strip()
        )  # Normalize user_id to lowercase and strip whitespace
        self._name = name
        self._group_size = group_size
        self._preferred_environment = preferred_environment
        self._budget = budget
        self._period = period
        self._password_hash = password_hash

    # Getter for user_id
    @property
    def user_id(self):
        return self._user_id.lower().strip()

    # @user_id.setter
    # def user_id(self, user_id):
    #     self._user_id = user_id

    # Getter & Setter for name
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = str(name)

    # Getter & Setter for group_size
    @property
    def group_size(self):
        return self._group_size

    @group_size.setter
    def group_size(self, group_size):
        try:
            self._group_size = int(group_size)
        except (TypeError, ValueError):
            raise ValueError("Group size must be an integer")

    # Getter & Setter for preferred_environment
    @property
    def preferred_environment(self):
        return self._preferred_environment

    @preferred_environment.setter
    def preferred_environment(self, preferred_environment):
        if not isinstance(preferred_environment, list):
            raise TypeError("Preferred environment must be a list.")
        self._preferred_environment = preferred_environment

    # Getter & Setter for budget
    @property
    def budget(self):
        return self._budget

    @budget.setter
    def budget(self, budget):
        budget = float(budget)
        if budget < 0:
            raise ValueError("Budget cannot be negative.")
        self._budget = budget

    # Getter & Setter for password_hash
    @property
    def password_hash(self):
        return self._password_hash

    # def set_password(self, raw_password):
    #     self._password_hash = hashlib.sha256(raw_password.encode()).hexdigest()

    # Getter & Setter for period
    @property
    def period(self):
        return self._period

    @period.setter
    def period(self, period):
        period = int(period)
        if period < 0:
            raise ValueError("Period cannot be negative.")
        self._period = int(period)

    def verify_password(self, raw_password):
        if not self._password_hash:
            return False
        return self._password_hash == hashlib.sha256(raw_password.encode()).hexdigest()

    def to_dict(self):
        """Convert User instance to a dictionary"""
        return {
            "user_id": self._user_id,
            "name": self._name,
            "group_size": self._group_size,
            "preferred_environment": self._preferred_environment,
            "budget": self._budget,
            "period": self._period,
            "password_hash": self._password_hash,
        }

    @classmethod
    def from_dict(cls, data):
        """Create a User instance from a dictionary"""
        return cls(
            user_id=data.get("user_id"),
            name=data.get("name"),
            group_size=data.get("group_size", 1),
            preferred_environment=data.get("preferred_environment", []),
            budget=data.get("budget", 0.0),
            period=data.get("period", 1),
            password_hash=data.get("password_hash"),
        )

    def __repr__(self):
        return f"User(user_id={self._user_id}, name={self._name}, group_size={self._group_size}, preferred_environment={self._preferred_environment}, budget={self._budget}, period={self._period})"
