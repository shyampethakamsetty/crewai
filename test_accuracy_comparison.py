#!/usr/bin/env python3
"""
Comprehensive accuracy test for all sentence processing models.
Tests each model individually and compares results.
"""

import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from market_analysis.tools.parallel_tool import ParallelSentenceProcessorTool

def create_test_transcript() -> str:
    """Create a test transcript with financial content"""
    return """hey listen If you're selling put options you might not even know which kind of account you're using I get a lot of questions about this People ask me they say "Lee should I be using a cash account or a margin account when I'm selling put options What's the difference And is there am I paying interest on on this margin I can you explain a little bit more?" in this video we will be talking about what you do when you sell put options and what type of account you can be using and how it works Whether you're using a cash secured or a margin account we're going to go over that I'm going to bring up the brokerage screen We're going to look at some examples of selling put options What margin requirement and or cash secured amount will be to make the trade All right I want to clear up a lot of things People are confused about this let's jump right in All right everyone and Lee Loel here from smart optionsceller.com Right in front of you you will see the margin rules for selling put options Now for those of you that don't even know what selling put options are it's when you sell a put option contract as your initial transaction You're not buying it and you're not owning it prior You're selling it you're creating it out of thin air You're selling a put option which means you're obligating yourself to potentially buy shares of a stock sometime down the road at a certain price which is called the strike price And for your obligation you're going to get paid money right up front to do that And we'll look at some examples and I'll show you what that exactly means But for those of you that are selling put options that or who want to sell put options you may not even know what kind of account you're already using to sell those put options what we're going to do is here I'm going to go over some quick little rules here then we'll look at the examples When you have a brokerage account whether you're you know buying stocks selling stocks trading options whatever it's either going to be what's called a cash account or a margin account Two different types Most people start off with a cash account And and on the application when you're filling out the broker application to open the account you'll come to a section that says "Do you want to add margin trading features to this account?" A lot of people don't even know what that means but in this case we always use in in our newsletter and I personally always use a margin account And if you have a cash account right now you can always change it to a margin account You have to fill out another form at your broker But the two types are either a cash account or a margin account And when you sell a put option contract you do have to put up some money to make that trade Just if you bought a stock you have to pay for that stock When you sell a put option since the bottom line might be that you might end up buying shares of stock your broker is going to require you to have some skin in the game and have some money on hold while the trade is active Now if you have a cash account it's going to be what's called a cash secured put option You are going to sell a cash secured put option or when you sell a put option you will have what's called a margin requirement there's two different things If in if you're using a cash account you will have what's called selling cash secured put options If you have a margin account number two you will have what's called a margin requirement And we will go over that And and these two amounts of money are completely different Okay And the one thing that people get confused about is when they have either the margin requirement or the cash secured money is never taken out of your account when you buy shares of stock you have to pay for those shares of stock Or when you buy options you have to pay for those options right up front and the money gets taken out of your account When you sell put options the money never leaves your account Money gets put on hold but it never leaves your account right here the money always stays in your account And the big one here is that no interest is ever paid ever when you're selling put options You are not borrowing money from anyone When you sell a put option you're using the cash that's already in your account to cover the collateral to sell that put option you're not borrowing any money to do this Okay People get confused about that And I I'll jump down to the bottom line here which when you sell put options this is not buying on margin Because the word margin is is thrown around here Some people will get confused What buying on margin is is if you want to buy shares of stock if you want to buy shares of stock on margin you will put up 50% of the cost to buy those shares of stock and then you will borrow the other 50% of the cost from your broker and they will charge you interest on that loan that they're they're giving you to buy the other half of the the shares of stock That's called buying on margin That is not what's happening when you sell put options When you sell put options it's either going to be a cash secured amount or what's called a margin requirement Money that's already in your account that's going to be held aside while the trade is active Okay let's quickly let's jump right into an example here and I'll show you what how that is Now let's quickly look at a stock chart here Now I pulled up a stock chart of Palanteer A lot of people might know Palanteer It's got a lot of activity of late Very popular stock It it it it's in the cyber security space for for governments around the world And the stock's been going up up up Alltime new highs here right You know under $140 a share let's assume that you're bullish on Palanteer and you want to potentially buy shares of Palanteer way down below where it's currently trading And you've designated I'm going to throw out a number here This is not a live recommendation This is not investment advice This is purely an example let's say you Palanteer and you want to get paid money to put an obligation to buy shares potentially at $75 a share which is all the way down here Okay here's the 75 level Palanteer's trading all the way up here yes when you sell a put option someone will pay you cash for your obligation Now in this case your obligation is to buy 100 shares at $75 a share while it's currently trading at a near 140 the chances of you buying the shares at 75 are very slim The only way that would come to fruition is if Palanteer actually fell from 140 all the way down to 75 before the expiration date of your option If it did fall that far then you'd have to follow through and buy your 100 shares at $75 a share But you'd be getting a nice over $60 discount from where it was currently trading when you first initiated the trade if you if you say to yourself okay I'll step up to the plate and buy shares at 75 if that ever happens In the meantime someone's going to pay you cash to do that when you initially sell that $75 put option you have to put up some money or have some money in your account that's going to be off limits held aside while this trade is active Let's go to the the option chain Okay so here's my broker platform This is an option chain I got Palanteer pulled up This is a symbol PLTR put options on the right hand side here Bid ask comms strike right here we're going to assume that we want to sell a $75 put option and we we're choosing September the September expiration date which is 90 days from today Now I make these these videos on the weekend so some of these numbers might be a little bit off from what you see during market hours and some of the margin margin requirement numbers may be a little off as well since the market is not open But I'm still going to show you everything you're keying in on Palanteer It's at 137.50 last price in the aftermarket hours You want to sell the 75 puts Collect some cash And then you want to see how much money is going to be required for you to make that transaction You sell the 75 put Here's how it went out 96 bid at 106 offer at the end of closing let's assume you can sell this thing for a dollar per contract Right in the middle somewhere That means if you sell this thing for a dollar per contract you're going to get $100 in your pocket right up front for selling that put option And now you have the obligation to buy 100 shares at $75 a share until September 19th 2025 the only way you'd have to fulfill your obligation is if Palanteer fell all the way down to 75 by the expiration date If it never falls that far you'll keep that that $100 that you're trying to get and you move on to the next trade But so let's assume you're going to so you're going to sell this thing Now the way you invoke that in in this trader platform is that you click on the bid price Okay let me move myself over here a little bit Click on the bid price 96 And it's going to bring up a a line here an order line and you're going to sell this thing And we want to sell it for $1 per contract When you click on transmit it's going to bring up another window that shows you what's actually going to happen how much money you need to actually sell this thing Now don't worry about this This is this is what's called a fake money account paper trading account you don't have to worry about these these warning messages in here this is the the box that comes up before you actually enter the trade you're going to sell we want to sell one contract of this Palenter 75 put And here's how it works And you're going to get try to get a $100 for it And on the right side of this this screen here it tells you what's going to happen after the trade or if the trade executes and how much money Now in this fake money account right now there's over $1.1 million in it Okay And you see there's 0 right here There's no other positions in this account Okay When you sell a put option if you have a margin account like this account is it's going to tell you how much money you have to hold aside in order to sell this $75 put option contract before the trade occurs you have $1.1 million in the account And there's no margin requirement whatsoever Now if you make the trade this is what happens what's called post trade So after the the trade is over you're going to get your account value is going to go up by almost $100 because if you're successful selling this thing you're going to get $100 put right into your account you can see here's your beginning balance here's your ending balance and it's going up by almost $100 less some commissions But here's the numbers that you want to concentrate on What's called the initial margin in order to sell the $75 put option you know the endgame may be you might have to come up with $7,500 to buy those 100 shares Now you don't know if you're going to end up buying the shares yet because you don't know if Palanteer is going to fall to 75 yet But in this case the broker still needs you to have some skin in the game they're going to ask you to hold some money aside Out of that 1.1 million they're going to ask you to hold aside $2,529 That's off limits now you'll have less $1.1 million but you cannot use $2500 of it Okay That's going to be off limits And the broker's going to make sure there's $2,500 2529 that is off limits I mean you still have a big chunk here But for smaller accounts we'll talk about those numbers after you execute the trade there's $2,529 that's off limits out of that potential $7,500 that you may have to come up with at the end if Palanteer does fall that far Okay let's talk about what that number is how much money that actually is if you have to come up with $7,500 in the end if it comes to fruition $2529 divided by 7500 is roughly 33.7% your broker is only asking you to hold aside 33.7% of that full $7,500 that you may have to come up with at the end Okay You don't know if you're going to buy the shares You don't know if you're going to have to come up with the full $7500 but in the meantime your broker's telling you you have to initially come up with $2,529"""

def analyze_sentence_quality(sentences: List[str], original_text: str) -> Dict[str, Any]:
    """Analyze the quality of sentence splitting"""
    if not sentences:
        return {
            "total_sentences": 0,
            "avg_length": 0,
            "financial_patterns": 0,
            "quality_score": 0.0
        }
    
    # Financial patterns to look for
    financial_patterns = [
        r'\$\d+(?:\.\d{2})?',  # Dollar amounts
        r'\d+(?:\.\d{1,2})?%',  # Percentages  
        r'\b[A-Z]{2,5}\b',  # Potential tickers (PLTR)
        r'\b\d+(?:\.\d+)?\b',  # Numbers
    ]
    
    total_financial_patterns = 0
    total_length = sum(len(s) for s in sentences)
    avg_length = total_length / len(sentences)
    
    for sentence in sentences:
        for pattern in financial_patterns:
            if re.search(pattern, sentence):
                total_financial_patterns += 1
                break  # Count once per sentence
    
    # Quality metrics
    length_score = min(1.0, avg_length / 150)  # Prefer ~150 char sentences
    pattern_score = total_financial_patterns / len(sentences)
    coverage_score = min(1.0, total_length / len(original_text))
    
    quality_score = (length_score * 0.3 + pattern_score * 0.4 + coverage_score * 0.3)
    
    return {
        "total_sentences": len(sentences),
        "avg_length": avg_length,
        "financial_patterns": total_financial_patterns,
        "pattern_ratio": pattern_score,
        "coverage_ratio": coverage_score,
        "quality_score": quality_score
    }

def test_all_models_accuracy(transcript: str) -> Dict[str, Any]:
    """Test all models with transformers enabled"""
    print("COMPREHENSIVE MODEL ACCURACY TEST")
    print("=" * 60)
    print(f"Test transcript: {len(transcript)} characters")
    print()
    
    results = {}
    
    # Test with 2 workers (optimal performance)
    print("Testing with ALL MODELS ENABLED (2 workers)...")
    start_time = time.time()
    
    tool = ParallelSentenceProcessorTool(max_workers=2)
    result = tool.process_transcript(transcript, "youtube", "AllModelsTest")
    
    processing_time = time.time() - start_time
    
    if result["status"] == "success":
        data = result["data"]
        sentences = data["sentences"]
        
        # Analyze quality
        quality_analysis = analyze_sentence_quality(sentences, transcript)
        
        print(f"✅ SUCCESS")
        print(f"   Sentences: {data['sentence_count']}")
        print(f"   Chunks: {data['chunks_processed']}")
        print(f"   Processing time: {processing_time:.2f}s")
        print(f"   Average sentence length: {quality_analysis['avg_length']:.1f} chars")
        print(f"   Financial patterns found: {quality_analysis['financial_patterns']}")
        print(f"   Pattern ratio: {quality_analysis['pattern_ratio']:.2f}")
        print(f"   Quality score: {quality_analysis['quality_score']:.2f}")
        print()
        
        # Show some example sentences
        print("📝 SAMPLE SENTENCES:")
        for i, sentence in enumerate(sentences[:5]):
            print(f"   {i+1}. {sentence[:100]}{'...' if len(sentence) > 100 else ''}")
        print()
        
        # Check for specific financial terms
        financial_terms_found = []
        key_terms = ["$75", "$140", "PLTR", "33.7%", "$100", "$7,500", "$2,529"]
        
        for term in key_terms:
            found_in = []
            for i, sentence in enumerate(sentences):
                if term in sentence:
                    found_in.append(i+1)
            if found_in:
                financial_terms_found.append(f"{term}: sentences {found_in[:3]}")
        
        print("💰 FINANCIAL TERMS PRESERVATION:")
        for term_info in financial_terms_found[:5]:
            print(f"   ✅ {term_info}")
        
        results = {
            "status": "success",
            "processing_time": processing_time,
            "sentence_count": data['sentence_count'],
            "chunks_processed": data['chunks_processed'],
            "quality_analysis": quality_analysis,
            "financial_terms_found": len(financial_terms_found),
            "data": data
        }
        
    else:
        print(f"❌ FAILED: {result['message']}")
        results = {
            "status": "failed",
            "error": result['message'],
            "processing_time": processing_time
        }
    
    return results

def compare_with_previous_results():
    """Compare with previous results"""
    print("\n" + "=" * 60)
    print("COMPARISON WITH PREVIOUS RESULTS")
    print("=" * 60)
    
    try:
        # Load previous results
        with open("output/20250623/parallel_sentences_ParallelTest_2workers.json", "r") as f:
            previous_data = json.load(f)
        
        print("📊 PREVIOUS RESULTS (Limited Models):")
        print(f"   Sentences: {previous_data['sentence_count']}")
        print(f"   Processing time: {previous_data['processing_time_seconds']:.2f}s")
        print(f"   Method: {previous_data['processing_method']}")
        
        prev_quality = analyze_sentence_quality(
            previous_data["sentences"], 
            previous_data["original_transcript"]
        )
        print(f"   Quality score: {prev_quality['quality_score']:.2f}")
        
    except Exception as e:
        print(f"Could not load previous results: {e}")

def main():
    """Main test function"""
    transcript = create_test_transcript()
    
    # Test all models
    results = test_all_models_accuracy(transcript)
    
    # Compare with previous
    compare_with_previous_results()
    
    # Performance analysis
    if results["status"] == "success":
        print("\n" + "=" * 60)
        print("PERFORMANCE ANALYSIS")
        print("=" * 60)
        
        chars_per_second = len(transcript) / results["processing_time"]
        sentences_per_second = results["sentence_count"] / results["processing_time"]
        
        print(f"📈 Processing speed: {chars_per_second:.0f} chars/second")
        print(f"📈 Sentence generation: {sentences_per_second:.1f} sentences/second")
        
        if results["processing_time"] > 30:
            print("⚠️  Processing time > 30s - consider optimizing for production")
        elif results["processing_time"] > 60:
            print("🚨 Processing time > 60s - too slow for real-time use")
        else:
            print("✅ Processing time acceptable for batch processing")
            
        print(f"\n🎯 Quality Score: {results['quality_analysis']['quality_score']:.2f}/1.0")
        if results['quality_analysis']['quality_score'] > 0.7:
            print("✅ HIGH QUALITY sentence splitting")
        elif results['quality_analysis']['quality_score'] > 0.5:
            print("⚠️  MEDIUM QUALITY sentence splitting")
        else:
            print("🚨 LOW QUALITY sentence splitting - needs improvement")

if __name__ == "__main__":
    import re
    main() 