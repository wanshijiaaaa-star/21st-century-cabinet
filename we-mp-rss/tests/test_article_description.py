import unittest

from core.article_summary import (
    derive_article_description,
    finalize_article_description,
    is_duplicate_description,
)


class ArticleDescriptionTest(unittest.TestCase):
    def test_title_is_not_a_description(self):
        self.assertTrue(is_duplicate_description("公益人写作计划", " 公益人写作计划 "))
        self.assertTrue(is_duplicate_description("讲座笔记：科学", "讲座笔记: 科学"))

    def test_description_comes_from_cached_content(self):
        description = derive_article_description(
            "<p>公益人写作计划</p><p>这是正文的第一个有效段落，用来介绍计划内容。</p>",
            "公益人写作计划",
        )
        self.assertEqual(description, "这是正文的第一个有效段落，用来介绍计划内容。")

    def test_missing_content_stays_blank(self):
        self.assertEqual(derive_article_description("", "标题"), "")

    def test_long_description_is_short_and_ends_with_full_stop(self):
        description = finalize_article_description("这是一段没有句号的很长摘要" * 12)
        self.assertLessEqual(len(description), 77)
        self.assertTrue(description.endswith("。"))


if __name__ == "__main__":
    unittest.main()
