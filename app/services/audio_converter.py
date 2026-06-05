"""μ-law⇔PCM16変換とサンプリングレート変換（§2.2）

ratecvはチャンクをまたいで変換stateを保持する必要があるため、
接続ごと・方向ごとにstateを管理する。1接続につき本クラスのインスタンスを1つ生成する。
"""

import audioop

_SAMPLE_WIDTH = 2  # PCM16 = 2バイト
_CHANNELS = 1  # モノラル
_TWILIO_RATE = 8000  # Twilio μ-law
_GEMINI_RATE = 16000  # Gemini PCM16


class AudioConverter:
    def __init__(self) -> None:
        # 上り（8k→16k）と下り（16k→8k）でratecv stateを別々に保持する
        self._upstream_state = None
        self._downstream_state = None

    def twilio_to_gemini(self, mulaw_8k: bytes) -> bytes:
        """Twilio入力（μ-law 8kHz）→ Gemini入力（PCM16 16kHz）"""
        pcm_8k = audioop.ulaw2lin(mulaw_8k, _SAMPLE_WIDTH)
        pcm_16k, self._upstream_state = audioop.ratecv(
            pcm_8k,
            _SAMPLE_WIDTH,
            _CHANNELS,
            _TWILIO_RATE,
            _GEMINI_RATE,
            self._upstream_state,
        )
        return pcm_16k

    def gemini_to_twilio(self, pcm_16k: bytes) -> bytes:
        """Gemini出力（PCM16 16kHz）→ Twilio出力（μ-law 8kHz）"""
        pcm_8k, self._downstream_state = audioop.ratecv(
            pcm_16k,
            _SAMPLE_WIDTH,
            _CHANNELS,
            _GEMINI_RATE,
            _TWILIO_RATE,
            self._downstream_state,
        )
        return audioop.lin2ulaw(pcm_8k, _SAMPLE_WIDTH)
