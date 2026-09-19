from __future__ import annotations

import asyncio
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches, Pt

from config import Settings
from opencode_runner import OpenCodeRunner


class CreativeError(RuntimeError):
    pass


def _safe_filename(value: str, fallback: str) -> str:
    value = re.sub(r'[^\w.-]+', '_', value, flags=re.UNICODE).strip('._')
    return value[:80] or fallback


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = chr(96) * 3
    if text.startswith(fence):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        text = '\n'.join(lines).strip()

    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        try:
            value = json.loads(text[start:end + 1])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass

    raise CreativeError(
        'ChatGPT/OpenCode вернул ответ, который не удалось преобразовать в структуру презентации.'
    )


@dataclass
class TarotCard:
    name: str
    orientation: str


class CreativeService:
    def __init__(self, settings: Settings, runner: OpenCodeRunner):
        self.settings = settings
        self.runner = runner
        self.output_dir = settings.state_dir / 'generated'
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def _ask(self, prompt: str, title: str) -> str:
        result = await self.runner.run_general(prompt, session_title=title)
        if result.returncode != 0:
            raise CreativeError(result.output)
        return result.output.strip()

    async def draft_email(self, brief: str) -> str:
        return await self._ask(
            (
                'Напиши готовое письмо по заданию ниже. По умолчанию используй русский язык, '
                'если пользователь явно не просит другой. Верни только готовый текст: сначала '
                'строка "Тема: ...", затем тело письма. Не выдумывай факты, имена или адреса.\n\n'
                f'Задание:\n{brief}'
            ),
            'telegram-email',
        )

    async def create_presentation(self, brief: str, slides: int = 8) -> Path:
        slides = min(max(slides, 3), 20)
        text = await self._ask(
            (
                'Создай структуру профессиональной презентации. Верни СТРОГО JSON без markdown '
                'по схеме: {"title":"...", "subtitle":"...", "slides":[{"title":"...",'
                '"bullets":["...","..."]}]}. Заголовочный слайд НЕ включай в slides. '
                f'Нужно {slides - 1} содержательных слайдов. На каждом 3-6 коротких пунктов. '
                'Не выдумывай конкретные цифры и источники, если их нет в задании.\n\n'
                f'Задание пользователя:\n{brief}'
            ),
            'telegram-presentation',
        )
        deck = _extract_json(text)
        return await asyncio.to_thread(self._build_presentation, deck, slides)

    def _build_presentation(self, deck: dict, slides: int) -> Path:
        title = str(deck.get('title') or 'Презентация')
        subtitle = str(deck.get('subtitle') or '')
        slide_items = deck.get('slides')
        if not isinstance(slide_items, list) or not slide_items:
            raise CreativeError('Не удалось получить структуру слайдов.')

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        title_slide = prs.slides.add_slide(prs.slide_layouts[0])
        title_slide.shapes.title.text = title
        if len(title_slide.placeholders) > 1:
            title_slide.placeholders[1].text = subtitle

        for item in slide_items[:slides - 1]:
            if not isinstance(item, dict):
                continue
            slide = prs.slides.add_slide(prs.slide_layouts[1])
            slide.shapes.title.text = str(item.get('title') or 'Слайд')
            tf = slide.placeholders[1].text_frame
            tf.clear()
            bullets = item.get('bullets') or []
            if not isinstance(bullets, list):
                bullets = [str(bullets)]
            for idx, bullet in enumerate(bullets[:6]):
                p = tf.paragraphs[0] if idx == 0 else tf.add_paragraph()
                p.text = str(bullet)
                p.level = 0
                p.font.size = Pt(22)

        name = _safe_filename(title, 'presentation')
        path = self.output_dir / f'{name}_{uuid.uuid4().hex[:8]}.pptx'
        prs.save(path)
        return path

    async def create_image_prompt(self, brief: str) -> str:
        return await self._ask(
            (
                'Составь очень качественный промпт для генерации изображения в ChatGPT. '
                'Верни только готовый промпт без объяснений. Уточни композицию, стиль, освещение, '
                'камеру, окружение и важные детали, но не добавляй факты, которых нет в задании.\n\n'
                f'Задание:\n{brief}'
            ),
            'telegram-image-prompt',
        )

    async def create_video_prompt(self, brief: str) -> str:
        return await self._ask(
            (
                'Составь очень качественный промпт для генерации видео в ChatGPT/Sora. '
                'Верни только готовый промпт без объяснений. Укажи сцену, движение камеры, '
                'движение объектов, свет, темп, длительность и визуальный стиль.\n\n'
                f'Задание:\n{brief}'
            ),
            'telegram-video-prompt',
        )

    async def interpret_tarot(self, question: str, cards: list[TarotCard]) -> str:
        spread = '\n'.join(
            f'{idx + 1}. {card.name} — {card.orientation}'
            for idx, card in enumerate(cards)
        )
        return await self._ask(
            (
                'Сделай вдумчивую интерпретацию расклада Таро на русском языке. '
                'Подавай это как символический инструмент для размышления, а не как гарантированное '
                'предсказание будущего. Структура: значение каждой карты, общая картина, практический '
                'вопрос для размышления. Не утверждай неизбежность событий.\n\n'
                f'Вопрос: {question or "Общий расклад"}\n'
                f'Карты:\n{spread}'
            ),
            'telegram-tarot',
        )
