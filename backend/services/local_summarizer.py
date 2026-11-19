"""Deterministic, extractive fallback summarisation for college notices."""

import re
from collections import Counter


NOT_MENTIONED = 'Not mentioned in the notice'
_DATE_PATTERN = re.compile(
    r'\b(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)(?:\s*,?\s*\d{2,4})?|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{2,4})?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b')
_PHONE_PATTERN = re.compile(r'(?<!\d)(?:\+?\d{1,3}[ -]?)?(?:\(?\d{2,5}\)?[ -]?)?\d{6,10}(?!\d)')
_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z'-]{2,}")
_KEYWORDS = {
    'notice', 'important', 'deadline', 'last', 'date', 'submit', 'submission', 'register',
    'registration', 'exam', 'examination', 'event', 'meeting', 'seminar', 'workshop',
    'students', 'eligible', 'required', 'must', 'should', 'venue', 'contact', 'apply',
    'application', 'attendance', 'documents', 'form', 'schedule', 'commence',
}
_ACTION_WORDS = {'submit', 'register', 'apply', 'attend', 'bring', 'complete', 'collect', 'report', 'contact', 'pay', 'upload', 'download'}
_DEADLINE_WORDS = {'deadline', 'last date', 'submit', 'submission', 'apply by', 'before', 'due'}
_EVENT_WORDS = {'event', 'seminar', 'workshop', 'meeting', 'programme', 'program', 'exam', 'examination', 'commence', 'held'}


class LocalSummaryError(ValueError):
    """Raised when extracted text cannot be summarised safely."""


def summarize_notice(text: str, source_information: str, warnings: list[str]) -> dict[str, object]:
    """Build a structured extractive notice summary without network access."""
    sentences = _sentences(text)
    if not sentences:
        raise LocalSummaryError('No readable text was found in this document.')

    ranked = _rank_sentences(sentences)
    detailed_sentences = _select_nonredundant(ranked, _summary_size(len(sentences)))
    short_sentences = detailed_sentences[:min(2, len(detailed_sentences))]
    metadata = _extract_metadata(sentences)

    return {
        'short_summary': ' '.join(short_sentences),
        'detailed_summary': ' '.join(detailed_sentences),
        'important_dates': metadata['important_dates'],
        'target_audience': metadata['target_audience'],
        'department': metadata['department'],
        'urgency': metadata['urgency'],
        'action_items': metadata['action_items'],
        'important_instructions': metadata['important_instructions'],
        'source_information': f'{source_information} Summary generated locally from extracted notice text.',
        'uncertainty_warnings': list(dict.fromkeys(warnings + ['AI summarisation was unavailable; this is a local extractive summary.'])),
        'notice_title': metadata['notice_title'],
        'event_dates': metadata['event_dates'],
        'venue': metadata['venue'],
        'required_documents': metadata['required_documents'],
        'contact_information': metadata['contact_information'],
    }


def _sentences(text: str) -> list[str]:
    cleaned = re.sub(r'\[Page\s+\d+\]', ' ', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'[\t ]+', ' ', cleaned)
    abbreviations = {'B.Sc.': 'B§Sc§', 'M.Sc.': 'M§Sc§', 'Ph.D.': 'Ph§D§', 'Dr.': 'Dr§', 'Prof.': 'Prof§'}
    for original, protected in abbreviations.items():
        cleaned = cleaned.replace(original, protected)
    fragments = re.split(r'(?<=[.!?])\s+|\n+', cleaned)
    restored = [fragment.replace('§', '.') for fragment in fragments]
    return [re.sub(r'\s+', ' ', fragment).strip(' -•') for fragment in restored if len(re.sub(r'\s+', ' ', fragment).strip(' -•')) >= 12]


def _rank_sentences(sentences: list[str]) -> list[tuple[float, int, str]]:
    document_words = [word.lower() for sentence in sentences for word in _WORD_PATTERN.findall(sentence)]
    frequencies = Counter(word for word in document_words if word not in {'this', 'that', 'with', 'from', 'have', 'will', 'your', 'students'})
    ranked: list[tuple[float, int, str]] = []
    for index, sentence in enumerate(sentences):
        words = [word.lower() for word in _WORD_PATTERN.findall(sentence)]
        keyword_score = sum(2 for word in words if word in _KEYWORDS)
        frequency_score = sum(frequencies[word] for word in set(words)) / max(len(words), 1)
        date_score = 4 if _DATE_PATTERN.search(sentence) else 0
        number_score = 1 if re.search(r'\d', sentence) else 0
        position_score = max(0, 2 - index * 0.25)
        density_score = min(len(words), 28) / 14
        ranked.append((keyword_score + frequency_score + date_score + number_score + position_score + density_score, index, sentence))
    return sorted(ranked, key=lambda item: (-item[0], item[1]))


def _select_nonredundant(ranked: list[tuple[float, int, str]], limit: int) -> list[str]:
    selected: list[tuple[int, str]] = []
    for _, index, sentence in ranked:
        terms = set(word.lower() for word in _WORD_PATTERN.findall(sentence))
        if any(_similarity(terms, set(word.lower() for word in _WORD_PATTERN.findall(existing))) > 0.68 for _, existing in selected):
            continue
        selected.append((index, sentence))
        if len(selected) == limit:
            break
    return [sentence for _, sentence in sorted(selected)]


def _similarity(left: set[str], right: set[str]) -> float:
    return len(left & right) / max(len(left | right), 1)


def _summary_size(sentence_count: int) -> int:
    if sentence_count <= 2:
        return 1
    if sentence_count <= 6:
        return 2
    if sentence_count <= 12:
        return 3
    return 4


def _extract_metadata(sentences: list[str]) -> dict[str, object]:
    title = _title(sentences)
    dated = [(sentence, _dates(sentence)) for sentence in sentences]
    all_dates = _unique(date for _, dates in dated for date in dates)
    deadline_dates = _unique(date for sentence, dates in dated if _contains(sentence, _DEADLINE_WORDS) for date in dates)
    event_dates = _unique(date for sentence, dates in dated if _contains(sentence, _EVENT_WORDS) for date in dates)
    actions = _matching_sentences(sentences, _ACTION_WORDS, 4)
    instructions = _matching_sentences(sentences, _ACTION_WORDS | {'must', 'should', 'required', 'please'}, 4)
    documents = _matching_sentences(sentences, {'document', 'documents', 'certificate', 'id', 'photo', 'form', 'receipt'}, 3)
    return {
        'notice_title': title,
        'important_dates': deadline_dates or all_dates or [NOT_MENTIONED],
        'event_dates': event_dates or [NOT_MENTIONED],
        'target_audience': _first_sentence(sentences, {'student', 'students', 'eligible', 'applicant', 'participants', 'faculty'}) or NOT_MENTIONED,
        'venue': _venue(sentences),
        'required_documents': documents or [NOT_MENTIONED],
        'contact_information': _contact(sentences),
        'department': _first_sentence(sentences, {'department', 'cell', 'office', 'committee', 'faculty', 'school'}) or NOT_MENTIONED,
        'urgency': _urgency(sentences),
        'action_items': actions or [NOT_MENTIONED],
        'important_instructions': instructions or [NOT_MENTIONED],
    }


def _title(sentences: list[str]) -> str:
    for sentence in sentences[:3]:
        upper = sentence.upper()
        if 'NOTICE' in upper or (sentence.isupper() and len(sentence) <= 120):
            return sentence
    return sentences[0] if len(sentences[0]) <= 100 else NOT_MENTIONED


def _dates(sentence: str) -> list[str]:
    return [match.group(0) for match in _DATE_PATTERN.finditer(sentence)]


def _contains(sentence: str, phrases: set[str]) -> bool:
    lower = sentence.lower()
    return any(phrase in lower for phrase in phrases)


def _matching_sentences(sentences: list[str], keywords: set[str], limit: int) -> list[str]:
    matches = [(index, sentence) for index, sentence in enumerate(sentences) if _contains(sentence, keywords)]
    matches.sort(key=lambda item: (-sum(keyword in item[1].lower() for keyword in keywords), item[0]))
    return [sentence for _, sentence in matches[:limit]]


def _first_sentence(sentences: list[str], keywords: set[str]) -> str | None:
    return next((sentence for sentence in sentences if _contains(sentence, keywords)), None)


def _venue(sentences: list[str]) -> str:
    for sentence in sentences:
        if re.search(r'\b(venue|location|auditorium|hall|room|campus|online)\b', sentence, re.IGNORECASE):
            return sentence
    return NOT_MENTIONED


def _contact(sentences: list[str]) -> str:
    for sentence in sentences:
        if _EMAIL_PATTERN.search(sentence) or _PHONE_PATTERN.search(sentence) or 'contact' in sentence.lower():
            return sentence
    return NOT_MENTIONED


def _urgency(sentences: list[str]) -> str:
    text = ' '.join(sentences).lower()
    if any(word in text for word in ('urgent', 'immediately', 'last date', 'final deadline')):
        return 'High'
    if any(word in text for word in ('deadline', 'submit', 'due date')):
        return 'Medium'
    return 'Low'


def _unique(items):
    return list(dict.fromkeys(items))
