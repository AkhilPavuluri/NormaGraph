#!/usr/bin/env python3
"""
Environment Configuration Validator

Validates that environment configuration follows minimal GCP-native setup.
Enforces removal of deprecated services (Qdrant, Gemini API keys, etc.)
"""

import os
import sys
from typing import List, Dict, Tuple
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class EnvValidator:
    """Validates environment configuration for minimal GCP-native setup"""
    
    # Required variables
    REQUIRED = [
        "GOOGLE_CLOUD_PROJECT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ]
    
    # Required if using Vertex AI
    REQUIRED_IF_VERTEX = [
        "GOOGLE_GENAI_USE_VERTEXAI",
    ]
    
    # Deprecated variables (should NOT be set)
    DEPRECATED = [
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_SEARCH_ENGINE_ID",
        "GOOGLE_USE_OAUTH",
        "GROQ_API_KEY",
    ]
    
    # Optional variables (allowed but not required)
    OPTIONAL = [
        "GOOGLE_CLOUD_LOCATION",
        "GEMINI_MODEL",
        "EMBEDDING_MODEL",
        "EMBEDDING_DIMENSION",
        "EMBEDDING_PROVIDER",
        "DOCUMENT_AI_PROCESSOR_ID",
        "GCS_BUCKET_NAME",
        "PORT",
    ]
    
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
    
    def validate(self) -> Tuple[bool, List[str], List[str], List[str]]:
        """
        Validate environment configuration.
        
        Returns:
            (is_valid, errors, warnings, info)
        """
        self.errors.clear()
        self.warnings.clear()
        self.info.clear()
        
        # Check required variables
        self._check_required()
        
        # Check deprecated variables
        self._check_deprecated()
        
        # Check Vertex AI configuration
        self._check_vertex_ai()
        
        # Check service account
        self._check_service_account()
        
        # Generate summary
        is_valid = len(self.errors) == 0
        
        return is_valid, self.errors, self.warnings, self.info
    
    def _check_required(self):
        """Check required environment variables"""
        for var in self.REQUIRED:
            value = os.getenv(var)
            if not value:
                self.errors.append(f"❌ REQUIRED: {var} is not set")
            else:
                self.info.append(f"✅ {var} is set")
    
    def _check_deprecated(self):
        """Check for deprecated environment variables"""
        for var in self.DEPRECATED:
            value = os.getenv(var)
            if value:
                self.warnings.append(
                    f"⚠️ DEPRECATED: {var} is set but should be removed. "
                    f"This service is not part of the minimal GCP-native setup."
                )
    
    def _check_vertex_ai(self):
        """Check Vertex AI configuration"""
        use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower()
        
        if use_vertex != "true":
            self.errors.append(
                "❌ REQUIRED: GOOGLE_GENAI_USE_VERTEXAI must be set to 'True'. "
                "API keys are not allowed in production setup."
            )
        else:
            self.info.append("✅ Using Vertex AI (not API keys)")
        
        # Check for API keys if using Vertex AI
        if use_vertex == "true":
            if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
                self.warnings.append(
                    "⚠️ API keys detected but GOOGLE_GENAI_USE_VERTEXAI=True. "
                    "API keys are redundant and should be removed."
                )
    
    def _check_service_account(self):
        """Check service account configuration"""
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if creds_path:
            # Remove quotes if present
            creds_path = creds_path.strip('"\'')
            
            if not os.path.exists(creds_path):
                self.errors.append(
                    f"❌ Service account file not found: {creds_path}"
                )
            else:
                self.info.append(f"✅ Service account file exists: {creds_path}")
        else:
            # Check if using default credentials
            if os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is None:
                self.warnings.append(
                    "⚠️ GOOGLE_APPLICATION_CREDENTIALS not set. "
                    "Will attempt to use default credentials."
                )
    
    def print_report(self):
        """Print validation report"""
        is_valid, errors, warnings, info = self.validate()
        
        print("=" * 80)
        print("Environment Configuration Validation Report")
        print("=" * 80)
        print()
        
        if info:
            print("✅ Configuration Status:")
            for msg in info:
                print(f"  {msg}")
            print()
        
        if warnings:
            print("⚠️ Warnings:")
            for msg in warnings:
                print(f"  {msg}")
            print()
        
        if errors:
            print("❌ Errors:")
            for msg in errors:
                print(f"  {msg}")
            print()
        
        print("=" * 80)
        if is_valid:
            print("✅ Environment configuration is VALID")
        else:
            print("❌ Environment configuration has ERRORS - please fix before proceeding")
        print("=" * 80)
        
        return is_valid


def main():
    """CLI entry point"""
    validator = EnvValidator()
    is_valid = validator.print_report()
    
    # Exit with error code if validation failed
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()

