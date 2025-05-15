import os
import logging
from typing import List, Dict, Any, Optional, Type
from pydantic import BaseModel, Field
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core.bridge.pydantic import PrivateAttr
from llama_index.llms.openai import OpenAI # Assuming OpenAI is still the target LLM
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv

# Ensure logs directory exists
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename=os.path.join(LOG_DIR, 'extraction_process.log'),
    filemode='a'
)
logger = logging.getLogger(__name__)

# --- Enhanced ExtractionAnswer and Reference for all fields ---
class Reference(BaseModel):
    filename: str
    page: Optional[int] = None
    line: Optional[int] = None
    quote: Optional[str] = None

class ExtractionAnswer(BaseModel):
    answer: str
    context: Optional[str] = None
    quotes: Optional[List[str]] = None
    references: Optional[List[Reference]] = None
    agent_logic: Optional[str] = None
    missing_info: Optional[str] = None

class UserRightsQuestions(BaseModel):
    redemption_rights: ExtractionAnswer
    asset_segregation_issuer: ExtractionAnswer
    beneficial_ownership: ExtractionAnswer

class RegulatoryCoverQuestions(BaseModel):
    licenses: ExtractionAnswer
    licenses_relevant: ExtractionAnswer
    legal_jurisdiction: ExtractionAnswer
    asset_segregation_issuer: ExtractionAnswer
    asset_segregation_custodian: ExtractionAnswer

USER_RIGHTS_QUESTIONS = [
    ("redemption_rights", "Based only on the terms of service/legals, does it explicitly state that the issued token can be redeemed in exchange for the underlying token through the issuer? If redemptions are possible, are there any restrictions?"),
    ("asset_segregation_issuer", "Based only on the terms of service/legals or other materials provided, does it explicitly state that the underlying reserve assets are segregated from the operating entity?"),
    ("beneficial_ownership", "Based only on the terms of service/legals, does it explicitly state that the token holders are the beneficial owners of the underlying reserve assets?")
]

REGULATORY_COVER_QUESTIONS = [
    ("licenses", "What licenses and from what jurisdiction has the issuing entity obtained? Only include licenses related to the entity which issued the token. If other group entities have licenses, mention them but clarify they are not for the issuing entity. If the token is issued by multiple entities, include all. Highlight if licenses are not relevant. Include a short overview of each license and the issuing jurisdiction."),
    ("licenses_relevant", "Out of the licenses identified above, which if any specifically relate to the issuance of the type of asset it is (e.g. stablecoin, wrapped token)? List and explain."),
    ("legal_jurisdiction", "What is the legal jurisdiction of the token's issuing entity? If the issuer is DeFi native, note if there is no definitive jurisdiction."),
    ("asset_segregation_issuer", "Is there asset segregation from the issuing entity and the reserves? If yes, explain and provide sources. Look for keywords like Trust, segregated accounts, etc. Note if NA for smart contract control."),
    ("asset_segregation_custodian", "Is there asset segregation from the custodian and the reserves? If yes, explain and provide sources. Look for keywords like Trust, segregated accounts, etc. Note if NA for smart contract control.")
]

# --- Pydantic Schemas for Extraction (condensed for brevity, should match original intent) ---

class BaseFactorDetail(BaseModel):
    notes: Optional[str] = Field(default=None, description="Summary of findings, evidence, or gaps related to this factor.")

class LicensingRegistrationDetail(BaseFactorDetail):
    license_name: Optional[str] = Field(default=None, description="Name of the license or registration.")
    issuing_authority: Optional[str] = Field(default=None, description="Authority that issued the license.")
    jurisdiction: Optional[str] = Field(default=None, description="Jurisdiction of the license.")
    status: Optional[str] = Field(default=None, description="Current status of the license (e.g., Active, Pending, None).")

class RegulatoryOversightDetail(BaseFactorDetail):
    classification: Optional[str] = Field(default=None, description="Classification of regulatory oversight (e.g., High, Medium, Low, None).")
    primary_regulator: Optional[str] = Field(default=None, description="Primary regulatory body overseeing the token/issuer.")
    primary_jurisdiction: Optional[str] = Field(default=None, description="Primary jurisdiction of regulation.")

class ComplianceDetail(BaseFactorDetail):
    sec_registration_status: Optional[str] = Field(default=None, description="SEC registration status (e.g., Registered, Not Registered, Exempt).")
    fincen_msb_registration: Optional[str] = Field(default=None, description="FinCEN MSB registration status.")
    other_relevant_compliances: Optional[str] = Field(default=None, description="Other relevant regulatory compliances and their status.")

class RegulatoryClarityDetail(BaseFactorDetail):
    assessment: Optional[str] = Field(default=None, description="Assessment of regulatory clarity for the token strategy (e.g., Clear, Ambiguous, Unclear).")
    jurisdictional_variations: Optional[str] = Field(default=None, description="Notes on how regulatory treatment varies by jurisdiction.")

class RegulatoryFactors(BaseModel):
    licensing_and_registration: ExtractionAnswer
    regulatory_oversight_level: ExtractionAnswer
    compliance_with_specific_regulations: ExtractionAnswer
    clarity_of_regulatory_treatment_for_strategy: ExtractionAnswer

class IssuerLegalStructureDetail(BaseFactorDetail):
    entity_type: Optional[str] = Field(default=None, description="Legal entity type of the issuer (e.g., Foundation, Corporation, DAO).")
    jurisdiction_of_incorporation: Optional[str] = Field(default=None, description="Jurisdiction where the issuer is legally incorporated or based.")
    bankruptcy_remoteness_assessment: Optional[str] = Field(default=None, description="Assessment of bankruptcy remoteness (e.g., High, Moderate, Low).")
    bankruptcy_remoteness_supporting_mechanisms: Optional[str] = Field(default=None, description="Mechanisms supporting bankruptcy remoteness.")

class RedemptionRightsDetail(BaseFactorDetail):
    direct_redemption_for_users: Optional[bool] = Field(default=None, description="Can users directly redeem the token from the issuer?")
    conditions_or_limitations: Optional[str] = Field(default=None, description="Conditions or limitations on redemption rights.")
    process_clarity: Optional[str] = Field(default=None, description="Clarity of the redemption process.")

class ClaimOnReservesDetail(BaseFactorDetail):
    nature_of_claim: Optional[str] = Field(default=None, description="Nature of the user claim on reserves (e.g., Direct, Indirect, None).")
    enforceability: Optional[str] = Field(default=None, description="Enforceability of the claim on reserves.")

class UserRightsDetail(BaseFactorDetail):
    clarity_of_terms: Optional[str] = Field(default=None, description="Clarity of terms of service for users.")
    redemption_rights: Optional[RedemptionRightsDetail] = Field(default=None)
    claim_on_reserves: Optional[ClaimOnReservesDetail] = Field(default=None)
    governing_law_of_terms: Optional[str] = Field(default=None, description="Governing law for the terms of service.")

class LegalFactors(BaseModel):
    issuer_legal_structure: ExtractionAnswer
    user_rights_and_terms_of_service: ExtractionAnswer
    counterparty_risk_legal_agreements: ExtractionAnswer
    perfection_of_security_interests_in_collateral: ExtractionAnswer

# ... (Operational, Governance, Insurance factors would follow a similar pattern)
# For brevity, I will create simplified versions for these for now.

class TransparencyOfReserves(BaseFactorDetail):
    attestation_frequency: Optional[str] = Field(default=None)
    auditor_name: Optional[str] = Field(default=None)
    audit_report_accessibility: Optional[str] = Field(default=None)
    real_time_monitoring_availability: Optional[bool] = Field(default=None)

class QualityLiquidityOfReserves(BaseFactorDetail):
    asset_composition_breakdown: Optional[str] = Field(default=None)
    credit_quality_of_assets: Optional[str] = Field(default=None)
    liquidity_profile: Optional[str] = Field(default=None)

class ReservesManagement(BaseFactorDetail):
    operational_history_years: Optional[str] = Field(default=None)
    transparency_of_reserves: Optional[TransparencyOfReserves] = Field(default=None)
    quality_and_liquidity_of_reserve_assets: Optional[QualityLiquidityOfReserves] = Field(default=None)

class RedemptionMechanism(BaseFactorDetail):
    efficiency: Optional[str] = Field(default=None)
    reliability: Optional[str] = Field(default=None)
    associated_fees: Optional[str] = Field(default=None)

class CustodianDetail(BaseFactorDetail):
    custodian_name: Optional[str] = Field(default=None)
    assets_custodied: Optional[str] = Field(default=None)
    regulatory_status_of_custodian: Optional[str] = Field(default=None)
    assessed_quality_or_rating: Optional[str] = Field(default=None)

class OperationalFactors(BaseModel):
    reserves_management: ExtractionAnswer
    redemption_mechanism: ExtractionAnswer
    third_party_custodians_for_reserves: ExtractionAnswer

class GovernanceFactors(BaseModel):
    governance_framework_description: ExtractionAnswer
    role_of_token_holders: ExtractionAnswer
    smart_contract_governance: ExtractionAnswer
    collateral_management_governance: ExtractionAnswer
    strategy_parameter_control: ExtractionAnswer

class InsuranceFactors(BaseModel):
    insurance_on_reserve_assets: ExtractionAnswer
    insurance_for_strategy_specific_risks: ExtractionAnswer

class StablecoinSpecificFactors(BaseModel):
    regulatory_factors: Optional[RegulatoryFactors] = Field(default=None)
    legal_factors: Optional[LegalFactors] = Field(default=None)
    operational_factors: Optional[OperationalFactors] = Field(default=None)
    governance_factors: Optional[GovernanceFactors] = Field(default=None)
    insurance_factors: Optional[InsuranceFactors] = Field(default=None)

class ExtractionSummary(BaseModel):
    overall_confidence: Optional[str] = Field(default=None, description="Overall confidence in the extracted information (High, Medium, Low).")
    key_findings_or_gaps: Optional[str] = Field(default=None, description="Key findings or information gaps identified during extraction.")

class DocumentSource(BaseModel):
    document_name_or_url: str
    document_type: Optional[str] = Field(default="Unknown") # e.g., Whitepaper, Blog Post, Terms of Service

class TokenAnalysisSchema(BaseModel):
    token_name: Optional[str] = Field(default=None, description="The official name of the token.")
    token_symbol: Optional[str] = Field(default=None, description="The official symbol of the token (e.g., USDC, DAI).")
    token_type_methodology: Optional[str] = Field(default=None, description="The type or methodology of the token (e.g., Fiat-backed Stablecoin, Algorithmic Stablecoin, RWA-backed).")
    source_documents_analyzed: Optional[List[DocumentSource]] = Field(default=None, description="List of source documents used for this analysis.")
    extraction_summary: Optional[ExtractionSummary] = Field(default=None, description="A high-level summary of the extraction process and findings.")
    stablecoin_specific_factors: Optional[StablecoinSpecificFactors] = Field(default=None)
    user_rights_questions: Optional[UserRightsQuestions] = None
    regulatory_cover_questions: Optional[RegulatoryCoverQuestions] = None
    custodian_wrapped_token_factors: Optional[Dict[str, Any]] = Field(default=None, description="Factors specific to custodian/wrapped tokens.")
    lst_factors: Optional[Dict[str, Any]] = Field(default=None, description="Factors specific to Liquid Staking Tokens.")
    general_notes_or_concerns: Optional[str] = Field(default=None, description="Any general notes, concerns, or red flags not covered elsewhere.")

    _documents: List[Document] = PrivateAttr(default_factory=list)

    def add_document_source(self, name_or_url: str, doc_type: Optional[str] = "Unknown"):
        if self.source_documents_analyzed is None:
            self.source_documents_analyzed = []
        self.source_documents_analyzed.append(DocumentSource(document_name_or_url=name_or_url, document_type=doc_type))

# --- LLM and Extraction Program Setup ---

# Ensure OPENAI_API_KEY is set in the environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY environment variable not set. LLM calls may fail.")
    # raise ValueError("OPENAI_API_KEY environment variable not set.")

LLM_MODEL = "gpt-4-1106-preview" # Or gpt-4.1 if that was the final model used

def get_llm():
    return OpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, temperature=0.0)

def create_extraction_program(output_cls: Type[BaseModel], prompt_template_str: str, llm: OpenAI) -> LLMTextCompletionProgram:
    return LLMTextCompletionProgram.from_defaults(
        output_cls=output_cls,
        llm=llm,
        prompt_template_str=prompt_template_str,
        verbose=True
    )

# --- Document Loading and Processing ---

def load_documents_from_sources(file_paths: Optional[List[str]] = None, urls: Optional[List[str]] = None) -> List[Document]:
    documents = []
    if file_paths:
        for file_path in file_paths:
            try:
                logger.info(f"Loading document from file: {file_path}")
                # SimpleDirectoryReader expects a directory, so we pass the file path as a list to input_files
                filename = os.path.basename(file_path)
                reader = SimpleDirectoryReader(input_files=[file_path])
                docs = reader.load_data()
                for doc in docs:
                    doc.metadata["source_type"] = "file"
                    doc.metadata["source_name"] = filename 
                documents.extend(docs)
            except Exception as e:
                logger.error(f"Failed to load document {file_path}: {e}")
    # URL loading can be added here if needed, using appropriate LlamaIndex loaders
    if urls:
        logger.warning("URL loading is not fully implemented in this recreated script version.")
        # Example: from llama_index.readers.web import SimpleWebPageReader
        # for url in urls:
        #     try:
        #         url_docs = SimpleWebPageReader(html_to_text=True).load_data([url])
        #         for doc in url_docs:
        #             doc.metadata["source_type"] = "url"
        #             doc.metadata["source_name"] = url
        #         documents.extend(url_docs)
        #     except Exception as e:
        #         logger.error(f"Failed to load document from URL {url}: {e}")

    logger.info(f"Loaded {len(documents)} documents in total.")
    return documents

# --- Enhanced Prompt Template ---
PROMPT_TEMPLATE_BASE = """
Given the following document context, extract the information relevant to the fields described below.
For each field, provide:
- The answer itself
- Supporting context
- Direct quote(s) from the document(s)
- Reference(s) (filename, page, line)
- Your reasoning as the agent
- If not enough information is available, state what is missing or what would help form a conclusion.

Context:
{context_str}

Desired output format is a JSON object matching the Pydantic schema for {factor_name}.
"""

# --- Extraction Logic Update ---
def run_extraction_for_factor(program: LLMTextCompletionProgram, documents: List[Document], factor_name: str) -> Optional[BaseModel]:
    full_text_context = "\n\n---\n\n".join([doc.get_content() for doc in documents])
    if len(full_text_context) > 100000:
        logger.warning(f"Context for {factor_name} is very long ({len(full_text_context)} chars), truncating.")
        full_text_context = full_text_context[:100000]
    if not full_text_context.strip():
        logger.warning(f"No text context available for factor: {factor_name}")
        return None
    try:
        logger.info(f"Running extraction for factor: {factor_name}")
        result = program(context_str=full_text_context, factor_name=factor_name)
        logger.info(f"Successfully extracted data for {factor_name}.")
        return result
    except Exception as e:
        logger.error(f"Error during extraction for {factor_name}: {e}")
        return None

def extract_token_information_iteratively(
    documents: List[Document],
    token_name: Optional[str] = None,
    token_symbol: Optional[str] = None,
    token_type_methodology: Optional[str] = None,
    additional_context: Optional[str] = None
) -> TokenAnalysisSchema:
    llm = get_llm()
    final_analysis = TokenAnalysisSchema(
        token_name=token_name,
        token_symbol=token_symbol,
        token_type_methodology=token_type_methodology
    )
    unique_sources = set()
    for doc in documents:
        source_name = doc.metadata.get("source_name", "Unknown Document")
        unique_sources.add(source_name)
    for source_name in unique_sources:
        final_analysis.add_document_source(name_or_url=source_name)
    # Extract all main factors
    factor_map = {
        "RegulatoryFactors": RegulatoryFactors,
        "LegalFactors": LegalFactors,
        "OperationalFactors": OperationalFactors,
        "GovernanceFactors": GovernanceFactors,
        "InsuranceFactors": InsuranceFactors,
    }
    extracted_stablecoin_factors = StablecoinSpecificFactors()
    for factor_name_cls, factor_cls in factor_map.items():
        logger.info(f"Preparing to extract {factor_name_cls}")
        prompt = PROMPT_TEMPLATE_BASE
        program = create_extraction_program(output_cls=factor_cls, prompt_template_str=prompt, llm=llm)
        extracted_data = run_extraction_for_factor(program, documents, factor_name_cls)
        if extracted_data:
            field_name_in_stablecoin_factors = factor_name_cls.lower().replace("factors", "_factors")
            if hasattr(extracted_stablecoin_factors, field_name_in_stablecoin_factors):
                setattr(extracted_stablecoin_factors, field_name_in_stablecoin_factors, extracted_data)
            else:
                logger.warning(f"Schema mismatch: Could not find field {field_name_in_stablecoin_factors} in StablecoinSpecificFactors for {factor_name_cls}")
        else:
            logger.warning(f"No data extracted for {factor_name_cls}")
    final_analysis.stablecoin_specific_factors = extracted_stablecoin_factors
    # Extract User Rights Questions
    user_rights_answers = {}
    for key, question in USER_RIGHTS_QUESTIONS:
        logger.info(f"Extracting user rights question: {key}")
        prompt = f"""
For the following question, provide:
- The answer itself
- Supporting context
- Direct quote(s) from the document(s)
- Reference(s) (filename, page, line)
- Your reasoning as the agent
- If not enough information is available, state what is missing or what would help form a conclusion.

Question: {question}

Context:
{{context_str}}
"""
        program = create_extraction_program(output_cls=ExtractionAnswer, prompt_template_str=prompt, llm=llm)
        answer = run_extraction_for_factor(program, documents, key)
        user_rights_answers[key] = answer
    final_analysis.user_rights_questions = UserRightsQuestions(**user_rights_answers)
    # Extract Regulatory Cover Questions
    regulatory_cover_answers = {}
    for key, question in REGULATORY_COVER_QUESTIONS:
        logger.info(f"Extracting regulatory cover question: {key}")
        prompt = f"""
For the following question, provide:
- The answer itself
- Supporting context
- Direct quote(s) from the document(s)
- Reference(s) (filename, page, line)
- Your reasoning as the agent
- If not enough information is available, state what is missing or what would help form a conclusion.

Question: {question}

Context:
{{context_str}}
"""
        program = create_extraction_program(output_cls=ExtractionAnswer, prompt_template_str=prompt, llm=llm)
        answer = run_extraction_for_factor(program, documents, key)
        regulatory_cover_answers[key] = answer
    final_analysis.regulatory_cover_questions = RegulatoryCoverQuestions(**regulatory_cover_answers)
    # Placeholder for summary generation
    final_analysis.extraction_summary = ExtractionSummary(
        overall_confidence="Medium",
        key_findings_or_gaps="Summary generation not fully implemented in this recreated script."
    )
    logger.info("Iterative extraction process completed.")
    return final_analysis


if __name__ == "__main__":
    # This is a placeholder for direct script testing, similar to openai_advanced_processor.py
    logger.info("Starting standalone extraction process (recreated script).")
    
    # Example: Define PDF paths (these would come from the /home/ubuntu/upload directory)
    # Ensure these files exist if running standalone
    pdf_directory = "/home/ubuntu/upload"
    pdf_files = [os.path.join(pdf_directory, f) for f in os.listdir(pdf_directory) if f.endswith(".pdf")]

    if not pdf_files:
        logger.error(f"No PDF files found in {pdf_directory}. Cannot run standalone test.")
    else:
        logger.info(f"Found PDF files for processing: {pdf_files}")
        documents_to_process = load_documents_from_sources(file_paths=pdf_files)
        
        if documents_to_process:
            # Example token details (these would typically come from user input in the app)
            analysis_result = extract_token_information_iteratively(
                documents=documents_to_process,
                token_name="Ethena USDe (Recreated Test)",
                token_symbol="USDe-Test",
                token_type_methodology="Stablecoin - Synthetic Dollar"
            )
            
            output_json_path = "/home/ubuntu/ethena_usde_extracted_data_recreated.json"
            try:
                with open(output_json_path, "w") as f:
                    f.write(analysis_result.model_dump_json(indent=2))
                logger.info(f"Extraction complete. Results saved to {output_json_path}")
            except Exception as e:
                logger.error(f"Failed to save extraction results: {e}")
        else:
            logger.error("No documents were loaded. Cannot proceed with extraction.")

