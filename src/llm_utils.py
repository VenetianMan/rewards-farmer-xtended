import os
import re
import random
<<<<<<< HEAD
import requests
import os
from constants import REPO_ROOT
=======
import time
from pathlib import Path
from typing import Generator, Optional, List, Tuple
import urllib.request
import json
import ollama
>>>>>>> my-custom-branch

from constants import (
	OLLAMA_HOST,
	DEFAULT_MODEL,
	MODEL_FALLBACK_PREFERENCES,
)

DEFAULT_SYSTEM_PROMPT_FOR_SEARCH_QUEST = (
	"You are a helpful assistant tasked with creating a search query based on a directive. "
	"Output nothing but the search query you create, and do not include any additional commentary or explanation. "
	"Do not include any labels or quotes. "
	"The search query must be the only output, and do not format the query as an imperative to 'search for' something. "
	"Imagine that your output will be fed directly into a search engine as you provide it. "
	"For example, if the directive is 'Search on Bing for the latest news about space exploration', you might output 'latest news space exploration'. "
	"Outputting 'search on Bing for the latest news about space exploration' or 'search bing.com/news for space exploration' would be incorrect, "
	"as those answers include instructions to perform a search rather than just the search query itself. "
	"Additionally, be specific, e.g. if a prompt asks you to search for vacation flights, include "
	"a specific destination rather than just searching 'vacation flights'. The current year is 2026. "
	"Make your query concise, ideally 6 words or less, and do not include any punctuation."
)

DEFAULT_USER_PROMPT_FOR_SEARCH_QUEST_WITHOUT_DESC = "Base your search query on the following task description: "

DEFAULT_SYSTEM_PROMPT_FOR_SEARCH_POINTS = (
	"The user is interested in learning more about topics related to a word that will be given to you. "
	"Your task is to come up with subsequent search queries that relate to each other, each one branching out "
	"from the previous one so that the user can explore a topic in depth. Your first search query should be "
	"based on the word that the user gives you, and each subsequent search query should be at least remotely based on the previous ones. "
	"Output only the single search query you come up with and do not include any additional commentary or explanation. Do not include any labels or quotes. "
	"The search queries should ideally be short (6 words max) and do not need to be fully fledged questions, but they should be unique. The current year is 2026."
)

DEFAULT_USER_PROMPT_FOR_SEARCH_POINTS_WITHOUT_DESC = "Generate the first search query based on the following word: "
USER_PROMPT_FOR_SEARCH_QUERY_CONTINUATION = "Generate the next search query."

# Load nouns safely relative to this file or project root
_NOUNS_FILE = Path(__file__).parent.parent / "nouns.txt"
if not _NOUNS_FILE.exists():
	_NOUNS_FILE = Path("nouns.txt")

<<<<<<< HEAD
MAX_EMPTY_RETRIES = 5
=======
if _NOUNS_FILE.exists():
	NOUNS = [
		noun.strip().lower() for noun in _NOUNS_FILE.read_text(encoding="utf-8").splitlines()
		if len(noun.strip()) >= 3
	]
else:
	NOUNS = ["technology", "astronomy", "geography", "history", "biology", "space", "weather", "music", "art"]

def get_random_noun() -> str:
	return random.choice(NOUNS)
>>>>>>> my-custom-branch

DEFAULT_LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local").strip().lower()

<<<<<<< HEAD
def _get_llm_base_url() -> str:
	if DEFAULT_LLM_PROVIDER in ("openrouter", "open-router"):
		return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip().rstrip("/")
	elif DEFAULT_LLM_PROVIDER in ("local", "ollama"):
		return os.getenv("LOCAL_LLM_BASE_URL", "http://localhost:11434/v1").strip().rstrip("/")
=======
# Client instance
_CLIENT = ollama.Client(host=OLLAMA_HOST, timeout=30)
_RESOLVED_MODEL: Optional[str] = None
_OLLAMA_AVAILABLE: Optional[bool] = None
>>>>>>> my-custom-branch

	raise ValueError(f"Unsupported LLM_PROVIDER: {DEFAULT_LLM_PROVIDER}. Supported values are 'openrouter' and 'local'.")

<<<<<<< HEAD
def _get_llm_model() -> str:
	if DEFAULT_LLM_PROVIDER in ("openrouter", "open-router"):
		return os.getenv("OPENROUTER_MODEL", "openrouter/free").strip()
	elif DEFAULT_LLM_PROVIDER in ("local", "ollama"):
		return os.getenv("LOCAL_LLM_MODEL", "gemma4:cloud").strip()
=======
def check_ollama_health(host: str = OLLAMA_HOST, timeout: float = 3.0) -> Tuple[bool, List[str], str]:
	"""Check connection to Ollama daemon and list locally installed models.
	
	Returns: (is_healthy, list_of_model_names, message)
	"""
	# Direct HTTP check first for fast timeout handling
	tags_url = f"{host.rstrip('/')}/api/tags"
	try:
		req = urllib.request.Request(tags_url, headers={"User-Agent": "RewardsFarmer/1.0"})
		with urllib.request.urlopen(req, timeout=timeout) as response:
			if response.status == 200:
				data = json.loads(response.read().decode("utf-8"))
				models = [m.get("name", "") for m in data.get("models", [])]
				return True, models, f"Connected to Ollama at {host} ({len(models)} models available)"
			return False, [], f"Ollama returned HTTP status {response.status}"
	except urllib.error.HTTPError as exc:
		if exc.code == 401:
			return False, [], f"Ollama authentication failed (HTTP 401 Unauthorized) at {host}"
		return False, [], f"Ollama HTTP error {exc.code} at {host}"
	except Exception as exc:
		return False, [], f"Could not connect to Ollama daemon at {host}: {exc}"
>>>>>>> my-custom-branch

	raise ValueError(f"Unsupported LLM_PROVIDER: {DEFAULT_LLM_PROVIDER}. Supported values are 'openrouter' and 'local'.")

<<<<<<< HEAD
def _get_llm_headers() -> dict[str, str]:
	headers = {
		"Content-Type": "application/json",
	}

	if DEFAULT_LLM_PROVIDER in {"openrouter", "open-router"}:
		api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
		if not api_key:
			raise RuntimeError("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")

		headers["Authorization"] = f"Bearer {api_key}"
		referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
		title = os.getenv("OPENROUTER_TITLE", "").strip()

		if referer:
			headers["HTTP-Referer"] = referer
		if title:
			headers["X-Title"] = title
		return headers

	api_key = os.getenv("LOCAL_LLM_API_KEY", "").strip()
	if api_key:
		headers["Authorization"] = f"Bearer {api_key}"

	return headers

def get_llm_response(messages: list[dict[str, str]]) -> str:
	response = requests.post(
		f"{_get_llm_base_url()}/chat/completions",
		headers=_get_llm_headers(),
		json={
			"model": _get_llm_model(),
			"messages": messages,
		},
		timeout=float(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "60")),
	)
	response.raise_for_status()

	content = response.json()["choices"][0]["message"]["content"]

	if not isinstance(content, str):
		raise RuntimeError(f"Unexpected LLM response content type: {type(content)!r}")

	return content

def get_nonempty_llm_response(messages: list[dict[str, str]]) -> str:
	"""Retry a bounded number of times instead of spinning forever on empties."""
	for attempt in range(MAX_EMPTY_RETRIES):
		response = get_llm_response(messages)
=======
def resolve_available_model(requested_model: str = DEFAULT_MODEL) -> Tuple[str, bool]:
	"""Resolve the best available local model, falling back through preferences or offline mode."""
	global _RESOLVED_MODEL, _OLLAMA_AVAILABLE
	
	healthy, installed_models, msg = check_ollama_health()
	_OLLAMA_AVAILABLE = healthy
	
	if not healthy:
		print(f"[WARNING] {msg}. Falling back to offline query synthesizer.")
		_RESOLVED_MODEL = "offline"
		return "offline", False
>>>>>>> my-custom-branch

	# Normalize installed model names (strip :latest tag for loose matching)
	installed_set = set(installed_models)
	base_installed_map = {m.split(":")[0]: m for m in installed_models}

	# 1. Exact match
	if requested_model in installed_set:
		_RESOLVED_MODEL = requested_model
		print(f"[INFO] Using requested Ollama model: {requested_model}")
		return requested_model, True

	# 2. Match without tag (e.g. requested 'llama3.2', found 'llama3.2:latest')
	req_base = requested_model.split(":")[0]
	if req_base in base_installed_map:
		matched = base_installed_map[req_base]
		_RESOLVED_MODEL = matched
		print(f"[INFO] Using matched Ollama model: {matched} (requested {requested_model})")
		return matched, True

	# 3. Fallback preference list
	for pref in MODEL_FALLBACK_PREFERENCES:
		pref_base = pref.split(":")[0]
		if pref in installed_set:
			_RESOLVED_MODEL = pref
			print(f"[INFO] Model '{requested_model}' not found. Falling back to preference: {pref}")
			return pref, True
		if pref_base in base_installed_map:
			matched = base_installed_map[pref_base]
			_RESOLVED_MODEL = matched
			print(f"[INFO] Model '{requested_model}' not found. Falling back to matched preference: {matched}")
			return matched, True

	# 4. Any installed model if list is non-empty
	if installed_models:
		fallback = installed_models[0]
		_RESOLVED_MODEL = fallback
		print(f"[INFO] Preferred models not found. Using installed model: {fallback}")
		return fallback, True

	print("[WARNING] Ollama is running but has no models installed. Falling back to offline query generator.")
	_RESOLVED_MODEL = "offline"
	return "offline", False


def get_active_model() -> str:
	global _RESOLVED_MODEL
	if _RESOLVED_MODEL is None:
		model, _ = resolve_available_model()
		_RESOLVED_MODEL = model
	return _RESOLVED_MODEL


# ======================================================================
# Offline Query Synthesizer (Fallback when Ollama is unavailable)
# ======================================================================

SEARCH_TEMPLATES = (
	"{noun} facts and history",
	"latest developments in {noun}",
	"best {noun} tips 2026",
	"how does {noun} work",
	"{noun} vs {noun2} comparison",
	"beginner guide to {noun}",
	"why is {noun} important in 2026",
	"interesting facts about {noun}",
	"top {noun} examples",
	"{noun} research and studies",
	"understanding {noun} concepts",
	"future of {noun} technology",
)

def get_fallback_search_query(seed_or_desc: str = "") -> str:
	"""Generate a realistic, randomized search query offline without LLM."""
	n1 = get_random_noun()
	n2 = get_random_noun()
	
	if seed_or_desc:
		cleaned = re.sub(r"(?i)\b(search\s+for|search\s+on\s+bing\s+for|find|explore|learn\s+about|look\s+up)\b", "", seed_or_desc)
		cleaned = re.sub(r"[^\w\s]", " ", cleaned).strip()
		words = [w for w in cleaned.split() if len(w) > 2]
		if words:
			extracted = " ".join(words[:4])
			return f"{extracted} 2026".strip().lower()

	template = random.choice(SEARCH_TEMPLATES)
	return template.format(noun=n1, noun2=n2).lower()


def get_fallback_related_queries(seed_word: str, num_queries: int = 20) -> Generator[str, None, None]:
	"""Generate a chain of themed search queries offline."""
	seed = seed_word.strip().lower()
	subtopics = [
		f"{seed} definition and overview",
		f"{seed} history and origins",
		f"types of {seed}",
		f"{seed} applications and uses",
		f"{seed} benefits and advantages",
		f"future trends in {seed} 2026",
		f"{seed} best practices",
		f"{seed} tutorials and guide",
		f"{seed} vs {get_random_noun()}",
		f"innovations in {seed}",
		f"{seed} real world examples",
		f"{seed} statistics and facts",
	]
	
	for i in range(num_queries):
		if i < len(subtopics):
			yield subtopics[i]
		else:
			n = get_random_noun()
			yield f"{seed} {n} insights 2026"


# ======================================================================
# LLM Search Query Generation with Exponential Backoff
# ======================================================================

def get_ollama_response_with_retry(
	messages: List[dict],
	model: Optional[str] = None,
	max_retries: int = 3,
	base_delay: float = 1.0,
) -> Optional[str]:
	"""Execute Ollama chat with exponential backoff retries and jitter."""
	active_model = model or get_active_model()
	
	if active_model == "offline":
		return None

	for attempt in range(1, max_retries + 1):
		try:
			response = _CLIENT.chat(
				model=active_model,
				messages=messages,
				options={"temperature": 0.7, "top_p": 0.9}
			)
			content = response.message.content if hasattr(response, "message") else ""
			if content and content.strip():
				# Clean any markdown quotation marks or prefixes
				clean = content.strip().strip('"\'`').replace("\n", " ").strip()
				return clean
			print(f"[WARNING] Empty response from Ollama (attempt {attempt}/{max_retries})")
		except Exception as exc:
			print(f"[WARNING] Ollama query failed (attempt {attempt}/{max_retries}): {exc}")

		if attempt < max_retries:
			backoff = base_delay * (2 ** (attempt - 1)) + random.uniform(0.2, 0.8)
			time.sleep(backoff)

	return None

def get_search_query_from_task_description(task_description: str) -> str:
	"""Extract search query from card task description using Ollama or offline fallback."""
	# Compatibility check
	if "lyrics of your favorite song" in task_description.lower():
		return "sweet caroline lyrics"

	messages = [
		{"role": "system", "content": DEFAULT_SYSTEM_PROMPT_FOR_SEARCH_QUEST},
		{"role": "user", "content": DEFAULT_USER_PROMPT_FOR_SEARCH_QUEST_WITHOUT_DESC + task_description}
	]

<<<<<<< HEAD
	try:
		response = get_nonempty_llm_response(messages)
		return response.lower()
	except Exception as exc:
		logger.warning("LLM is offline or unavailable (%s). Using fallback search query generator.", exc)
		words = [w for w in re.sub(r"[^\w\s]", "", task_description).split() if len(w) > 3 and w.lower() not in {"search", "bing", "find", "about", "with", "from", "that", "this"}]
		fallback_query = " ".join(words[:4]) if words else f"{get_random_noun()} search"
		return fallback_query.lower()
=======
	response = get_ollama_response_with_retry(messages)
	if response:
		return response.lower()

	# Fallback if Ollama unreachable
	return get_fallback_search_query(task_description)
>>>>>>> my-custom-branch


def get_related_search_queries(seed_word: str, num_queries: int = 20) -> Generator[str, None, None]:
	"""Generate chained, branching search queries for daily search quota."""
	active_model = get_active_model()
	
	if active_model == "offline":
		yield from get_fallback_related_queries(seed_word, num_queries)
		return

	messages = [
		{"role": "system", "content": DEFAULT_SYSTEM_PROMPT_FOR_SEARCH_POINTS},
		{"role": "user", "content": DEFAULT_USER_PROMPT_FOR_SEARCH_POINTS_WITHOUT_DESC + seed_word}
	]

	for _ in range(num_queries):
<<<<<<< HEAD
		if not use_fallback:
			try:
				response = get_nonempty_llm_response(messages)
				yield response.lower()
=======
		response = get_ollama_response_with_retry(messages, model=active_model)
>>>>>>> my-custom-branch

		if not response:
			# If LLM failed during batch, yield offline fallback
			yield get_fallback_search_query(seed_word)
			continue

<<<<<<< HEAD
				messages.append({
					"role": "user",
					"content": USER_PROMPT_FOR_SEARCH_QUERY_CONTINUATION
				})
				continue
			except Exception as exc:
				logger.warning("LLM is offline or unavailable (%s). Using built-in generator for remaining queries.", exc)
				use_fallback = True

		noun1 = get_random_noun()
		noun2 = get_random_noun()
		yield f"{seed_word} {noun1} {noun2}".lower()


NOUNS = [
	noun.strip().lower() for noun in open(os.path.join(REPO_ROOT, "nouns.txt"), "r", encoding="utf-8").read().splitlines()
	if len(noun.strip()) >= 3
]


def get_random_noun() -> str:
	return random.choice(NOUNS)
=======
		clean_query = response.lower()
		yield clean_query

		messages.append({"role": "assistant", "content": clean_query})
		messages.append({"role": "user", "content": USER_PROMPT_FOR_SEARCH_QUERY_CONTINUATION})
>>>>>>> my-custom-branch
