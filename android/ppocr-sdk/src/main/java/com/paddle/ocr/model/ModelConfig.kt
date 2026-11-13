
package com.paddle.ocr.model

import android.content.Context
import com.paddle.ocr.util.YamlUtils

data class ModelConfig(
    val characterList: List<String>,
) {
    companion object {
        fun parse(context: Context, assetPath: String): ModelConfig {
            val content = try {
                com.paddle.ocr.util.ModelSource.text(context, assetPath)
            } catch (t: Throwable) {
                throw OCRError.ConfigParseFailed(assetPath, t)
            }
            val characterDict = try {
                extractCharacterDict(content, assetPath)
            } catch (e: OCRError.ConfigParseFailed) {
                throw e
            } catch (t: Throwable) {
                throw OCRError.ConfigParseFailed(assetPath, t)
            }
            val charListWithSpace = characterDict.toMutableList().apply {
                if (lastOrNull() != " ") add(" ")
            }

            return ModelConfig(characterList = charListWithSpace)
        }

        fun fromDictText(content: String, dictPath: String): ModelConfig {
            val characters = content
                .replace("\r\n", "\n")
                .replace('\r', '\n')
                .lines()
                .filter { it.isNotEmpty() }
            if (characters.isEmpty()) {
                throw OCRError.ConfigParseFailed("Empty dict: $dictPath")
            }
            val charListWithSpace = characters.toMutableList().apply {
                if (lastOrNull() != " ") add(" ")
            }
            return ModelConfig(characterList = charListWithSpace)
        }

        private fun extractCharacterDict(content: String, assetPath: String): List<String> {
            val lines = content.replace("\r\n", "\n").replace('\r', '\n').lines()
            val postProcessLine = lines.indexOfFirst { it.trim() == "PostProcess:" }
            if (postProcessLine < 0) {
                throw OCRError.ConfigParseFailed("Missing PostProcess in $assetPath")
            }

            val postProcessIndent = YamlUtils.leadingSpaces(lines[postProcessLine])
            val characterDictLine = findCharacterDictLine(lines, postProcessLine + 1, postProcessIndent)
            if (characterDictLine < 0) {
                throw OCRError.ConfigParseFailed("Missing character_dict in $assetPath")
            }

            val characterDictIndent = YamlUtils.leadingSpaces(lines[characterDictLine])
            val characters = mutableListOf<String>()
            var lineIndex = characterDictLine + 1
            while (lineIndex < lines.size) {
                val line = lines[lineIndex]
                val indent = YamlUtils.leadingSpaces(line)
                val content = line.substring(indent)
                val keyLikeContent = content.trim()
                if (keyLikeContent.isEmpty() || keyLikeContent.startsWith("#")) {
                    lineIndex++
                    continue
                }

                if (!content.startsWith("-")) {
                    if (indent <= characterDictIndent) break
                    lineIndex++
                    continue
                }

                characters.add(parseYamlListScalar(content.substring(1)))
                lineIndex++
            }

            if (characters.isEmpty()) {
                throw OCRError.ConfigParseFailed("Empty character_dict in $assetPath")
            }
            return characters
        }

        private fun findCharacterDictLine(
            lines: List<String>,
            startLine: Int,
            postProcessIndent: Int,
        ): Int {
            var lineIndex = startLine
            while (lineIndex < lines.size) {
                val line = lines[lineIndex]
                val trimmed = line.trim()
                if (trimmed.isEmpty() || trimmed.startsWith("#")) {
                    lineIndex++
                    continue
                }
                val indent = YamlUtils.leadingSpaces(line)
                if (indent <= postProcessIndent) break
                if (trimmed == "character_dict:") return lineIndex
                lineIndex++
            }
            return -1
        }

        private fun parseYamlListScalar(rawValue: String): String {
            val value = rawValue.dropWhile { it == ' ' }
            if (value.length >= 2 && value.first() == '\'' && value.last() == '\'') {
                return value.substring(1, value.length - 1).replace("''", "'")
            }
            if (value.length >= 2 && value.first() == '"' && value.last() == '"') {
                return value.substring(1, value.length - 1)
                    .replace("\\\"", "\"")
                    .replace("\\\\", "\\")
                    .replace("\\n", "\n")
                    .replace("\\r", "\r")
                    .replace("\\t", "\t")
            }
            return value
        }
    }
}
