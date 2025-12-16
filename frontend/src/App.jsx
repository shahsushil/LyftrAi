import React, { useState, useMemo } from 'react';
import axios from 'axios';
import {
  ChakraProvider,
  Container,
  VStack,
  Heading,
  Input,
  Button,
  // Spinner, // Not used directly in App, removed for cleanliness
  Alert,
  AlertIcon,
  Box,
  Accordion,
  AccordionItem,
  AccordionButton,
  AccordionPanel,
  AccordionIcon,
  Text,
  Badge,
  Code,
  Divider,
  HStack,
  Link,
  useToast,
  IconButton, // Added for pagination controls
} from '@chakra-ui/react';
import { ChevronLeftIcon, ChevronRightIcon } from '@chakra-ui/icons'; // Added icons
import { JsonView, defaultStyles } from 'react-json-view-lite';
import 'react-json-view-lite/dist/index.css';

// --- Configuration ---
const SECTIONS_PER_PAGE = 10; // New: Define how many sections to show per page

// Component to display a single section nicely (UNMODIFIED)
const SectionViewer = ({ section }) => {
  return (
    <AccordionItem border="1px" borderColor="gray.200" borderRadius="md" my={2}>
      <h2>
        <AccordionButton bg="gray.50" _hover={{ bg: 'gray.100' }}>
          <Box flex="1" textAlign="left">
            <HStack spacing={3}>
              <Badge colorScheme={section.type === 'hero' ? 'purple' : 'teal'}>
                {section.type.toUpperCase()}
              </Badge>
              <Text fontWeight="semibold" isTruncated>
                {section.label || 'No Label'}
              </Text>
            </HStack>
          </Box>
          <AccordionIcon />
        </AccordionButton>
      </h2>
      <AccordionPanel pb={4} pt={4}>
        <VStack align="stretch" spacing={4}>
          <Text fontWeight="medium" fontSize="sm">
            Content Summary:
          </Text>
          <Code whiteSpace="pre-wrap" p={3} children={section.content.text.substring(0, 500) + (section.content.text.length > 500 ? '...' : '')} />

          <Divider />
          <Text fontWeight="medium" fontSize="sm">
            Full Section JSON:
          </Text>
          <Box p={3} border="1px" borderColor="gray.100" borderRadius="md" overflowX="auto" maxH="400px">
            <JsonView data={section} style={defaultStyles} shouldInitiallyExpand={(level) => level < 1} />
          </Box>
        </VStack>
      </AccordionPanel>
    </AccordionItem>
  );
};

// Component to display interactions and errors (UNMODIFIED)
const InteractionSummary = ({ interactions, errors }) => (
  <Box p={4} borderWidth="1px" borderRadius="lg" bg="white" shadow="sm">
    <Heading size="md" mb={2}>
      Interactions & Errors
    </Heading>
    <HStack spacing={4} wrap="wrap" mb={3}>
      <Badge colorScheme="blue">Clicks: {interactions.clicks.length}</Badge>
      <Badge colorScheme="blue">Scrolls: {interactions.scrolls}</Badge>
      <Badge colorScheme="blue">Pages Visited: {interactions.pages.length}</Badge>
    </HStack>
    
    <Text fontWeight="medium" mt={4}>Errors ({errors.length}):</Text>
    {errors.length > 0 ? (
      <VStack align="stretch" spacing={2} mt={2}>
        {errors.map((err, index) => (
          <Alert key={index} status="error" variant="left-accent">
            <AlertIcon />
            <Box>
              <Text fontWeight="bold">Phase: {err.phase.toUpperCase()}</Text>
              <Text fontSize="sm">{err.message}</Text>
            </Box>
          </Alert>
        ))}
      </VStack>
    ) : (
      <Text fontSize="sm" color="gray.500">No critical errors reported.</Text>
    )}
  </Box>
);

// --- NEW Pagination Component ---
const SectionsPagination = ({ totalSections, currentPage, onPageChange }) => {
    const totalPages = Math.ceil(totalSections / SECTIONS_PER_PAGE);

    // Don't show controls if there's only one page
    if (totalPages <= 1) return null;

    return (
        <HStack spacing={2} justifyContent="center" py={4}>
            <IconButton
                aria-label="Previous Page"
                icon={<ChevronLeftIcon />}
                onClick={() => onPageChange(currentPage - 1)}
                isDisabled={currentPage === 1}
                size="sm"
            />
            
            <Text>
                Page <Code colorScheme="purple">{currentPage}</Code> of <Code colorScheme="purple">{totalPages}</Code>
            </Text>

            <IconButton
                aria-label="Next Page"
                icon={<ChevronRightIcon />}
                onClick={() => onPageChange(currentPage + 1)}
                isDisabled={currentPage === totalPages}
                size="sm"
            />
        </HStack>
    );
};
// --- END NEW Pagination Component ---


const App = () => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1); // New State for Pagination
  const toast = useToast();

  const handleScrape = async () => {
    if (!url) {
      toast({ title: 'URL required.', status: 'warning', duration: 3000, isClosable: true });
      return;
    }

    setLoading(true);
    setResult(null);
    setError(null);
    setCurrentPage(1); // Reset page on new scrape

    try {
      const response = await axios.post('/scrape', { url });
      setResult(response.data.result);
      toast({ title: 'Scrape successful!', status: 'success', duration: 3000, isClosable: true });
    } catch (err) {
      console.error(err);
      const backendError = err.response?.data?.detail?.message || 'Failed to connect to backend.';
      setError(backendError);
      // Ensure result is cleared on failure unless you explicitly want to keep partial data
      setResult(null); 

      toast({ 
        title: 'Scrape Failed.', 
        description: backendError, 
        status: 'error', 
        duration: 5000, 
        isClosable: true 
      });
    } finally {
      setLoading(false);
    }
  };
  
  const handleDownload = () => {
    if (!result) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({ result }, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", `scrape_result_${new Date().toISOString()}.json`);
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  // --- New Logic: Calculate visible sections based on current page ---
  const paginatedSections = useMemo(() => {
    if (!result || !result.sections.length) return [];
    
    const startIndex = (currentPage - 1) * SECTIONS_PER_PAGE;
    const endIndex = startIndex + SECTIONS_PER_PAGE;
    
    return result.sections.slice(startIndex, endIndex);
  }, [result, currentPage]);

  const totalSections = result?.sections?.length || 0;
  // --- End New Logic ---

  return (
    <ChakraProvider>
      <Container maxW="container.xl" py={10}>
        <VStack spacing={8} align="stretch">
          <Heading as="h1" size="xl" textAlign="center" color="purple.600">
            Lyftr AI Universal Scraper
          </Heading>

          {/* ... Input/Button Box (Unmodified) ... */}
          <Box p={6} borderWidth="1px" borderRadius="lg" bg="gray.50">
            <VStack spacing={4}>
              <Input
                placeholder="Enter URL to Scrape (e.g., https://example.com)"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                size="lg"
                isDisabled={loading}
              />
              <Button
                colorScheme="purple"
                onClick={handleScrape}
                isLoading={loading}
                loadingText="Scraping..."
                size="lg"
                width="100%"
              >
                Start Scrape
              </Button>
            </VStack>
          </Box>

          {/* ... Error Alert (Unmodified) ... */}
          {error && (
            <Alert status="error" variant="left-accent">
              <AlertIcon />
              <Text>{error}</Text>
            </Alert>
          )}

          {result && (
            <VStack spacing={6} align="stretch">
              {/* ... Scrape Summary Box (Unmodified) ... */}
              <Box p={6} borderWidth="1px" borderRadius="lg" shadow="md" bg="white">
                <Heading size="md" mb={4}>Scrape Summary</Heading>
                <VStack align="stretch" spacing={1} fontSize="sm">
                  <Text>
                    <strong>URL:</strong> <Link href={result.url} isExternal color="blue.500">{result.url}</Link>
                  </Text>
                  <Text>
                    <strong>Title:</strong> {result.meta.title || 'N/A'}
                  </Text>
                  <Text>
                    <strong>Language:</strong> {result.meta.language || 'N/A'}
                  </Text>
                  <Text>
                    <strong>Strategy:</strong> <Badge colorScheme={result.meta.strategy === 'js' ? 'orange' : 'green'}>{result.meta.strategy.toUpperCase()}</Badge>
                  </Text>
                  <Text>
                    <strong>Scraped At:</strong> {new Date(result.scrapedAt).toLocaleTimeString()}
                  </Text>
                </VStack>
                <HStack justifyContent="space-between" mt={4}>
                  <Button size="sm" onClick={handleDownload} colorScheme="teal" variant="outline">
                    Download Full JSON
                  </Button>
                  <Text fontSize="xs" color="gray.500">
                    {totalSections} Sections Found
                  </Text>
                </HStack>
              </Box>

              {/* ... Interaction Summary (Unmodified) ... */}
              <InteractionSummary interactions={result.interactions} errors={result.errors} />

              {/* --- NEW Pagination and Sections Display --- */}
              <Heading size="md">Parsed Sections ({totalSections})</Heading>
              
              <SectionsPagination 
                totalSections={totalSections} 
                currentPage={currentPage} 
                onPageChange={setCurrentPage} 
              />

              <Accordion allowMultiple defaultIndex={[0]} width="100%">
                {paginatedSections.length > 0 ? (
                  paginatedSections.map((section, index) => (
                    // Use a unique key based on the page index and the section itself
                    <SectionViewer key={`section-${currentPage}-${index}`} section={section} />
                  ))
                ) : (
                  <Text color="gray.500">No sections could be extracted.</Text>
                )}
              </Accordion>

              <SectionsPagination 
                totalSections={totalSections} 
                currentPage={currentPage} 
                onPageChange={setCurrentPage} 
              />
              {/* --- END NEW Pagination and Sections Display --- */}
            </VStack>
          )}
        </VStack>
      </Container>
    </ChakraProvider>
  );
};

export default App;