"""
Policy module interface definition.

Defines the contract that all pluggable policy modules must implement.
"""

from abc import ABC, abstractmethod

from policy_engine.models import PolicyContext, PolicyResult


class PolicyModule(ABC):
    """
    Abstract base class for all policy modules.
    
    Every policy module must implement this interface. The policy engine
    orchestrates policy evaluation by calling evaluate() on registered modules.
    
    Policy modules are independent and should not import from each other.
    They only depend on PolicyContext and PolicyResult models.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the unique name of this policy module.
        
        Returns:
            Policy name (e.g., "pii_detection", "mnpi_check", "hipaa_compliance")
        """
        pass

    @abstractmethod
    def evaluate(self, context: PolicyContext) -> PolicyResult:
        """
        Evaluate the policy against the given context.
        
        This is the core method that each policy module must implement.
        It receives all request data via PolicyContext and returns a
        PolicyResult with the decision and reasoning.
        
        Args:
            context: PolicyContext containing all request data, user info,
                   metadata, and prior policy outcomes
            
        Returns:
            PolicyResult with outcome (ALLOW/BLOCK/REDACT/ESCALATE),
            reason, and any modified content
        """
        pass

    def configure(self, config: dict) -> None:
        """
        Configure the policy module with settings.
        
        Called during policy registration to pass configuration from
        the YAML config file. Override this if your policy needs configuration.
        
        Args:
            config: Dictionary of configuration values from config file
        """
        # Default implementation does nothing
        # Subclasses can override to handle their specific config
        pass

