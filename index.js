#!/usr/bin/env node

import Parser from 'rss-parser';
import { Command } from 'commander';
import chalk from 'chalk';

const parser = new Parser();
const program = new Command();

program
  .name('gnews')
  .description('A CLI to fetch the latest news from Google News')
  .version('1.0.0')
  .option('-s, --search <topic>', 'Search for a specific news topic')
  .option('-n, --number <limit>', 'Number of news items to fetch (default: 10)', 10)
  .action(async (options) => {
    try {
      const { search, number } = options;
      const limit = parseInt(number, 10);
      
      let feedUrl = 'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en';
      if (search) {
        console.log(chalk.blue(`\nFetching latest news for: "${search}"...`));
        // Encode the search query to handle spaces and special characters
        const query = encodeURIComponent(search);
        feedUrl = `https://news.google.com/rss/search?q=${query}&hl=en-US&gl=US&ceid=US:en`;
      } else {
        console.log(chalk.blue('\nFetching latest top news...'));
      }

      const feed = await parser.parseURL(feedUrl);
      
      console.log(chalk.bold.green(`\n=== ${feed.title} ===\n`));
      
      const items = feed.items.slice(0, limit);
      
      if (items.length === 0) {
        console.log(chalk.yellow('No news items found.'));
        return;
      }

      items.forEach((item, index) => {
        console.log(chalk.bold.cyan(`${index + 1}. ${item.title}`));
        console.log(chalk.gray(`   Published: ${new Date(item.pubDate).toLocaleString()}`));
        console.log(chalk.underline.blue(`   ${item.link}\n`));
      });

    } catch (error) {
      console.error(chalk.red('\nError fetching news:'), error.message);
      process.exit(1);
    }
  });

program.parse(process.argv);
