using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Azure.AI.OpenAI;
using Microsoft.Azure.Functions.Worker;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using OpenAI.Embeddings;

namespace CosmosEmbeddingGenerator;

public class CosmosEmbeddingGeneratorFunction
{
    private readonly ILogger _logger;
    private readonly AzureOpenAIClient _openAiClient;
    private readonly EmbeddingClient _embeddingClient;
    private readonly int _dimensions;
    private readonly string _vectorProperty;
    private readonly string _hashProperty;
    private readonly List<string> _propertiesToEmbed;

    public CosmosEmbeddingGeneratorFunction(ILoggerFactory loggerFactory, IOptions<CosmosEmbeddingOptions> configuration)
    {
        _logger = loggerFactory.CreateLogger<CosmosEmbeddingGeneratorFunction>();
        var config = configuration.Value;

        if (config is null)
        {
            throw new ArgumentNullException(nameof(config));
        }

        _openAiClient = new AzureOpenAIClient(new Uri(config.OpenAiEndpoint), new System.ClientModel.ApiKeyCredential(config.OpenAiApiKey));
        _embeddingClient = _openAiClient.GetEmbeddingClient(config.OpenAiDeploymentName);
        _dimensions = config.OpenAiDimensions;
        _vectorProperty = config.VectorProperty;
        _hashProperty = config.HashProperty;
        _propertiesToEmbed = config.PropertiesToEmbed;

    }

    /// <summary>
    /// This function listens for changes to new or existing CosmosDb documents/items,
    /// and updates them in place with vector embeddings.
    ///
    /// </summary>
    /// <param name="input">The list of documents that were modified in the CosmosDB container.</param>
    /// <param name="context">The execution context of the Azure Function.</param>
    /// <returns>A task that represents the asynchronous operation. The task result contains the updated documents with vector embeddings.</returns>
    [Function("CosmosListener")]
    [CosmosDBOutput(
        databaseName: "GAB2025",
        containerName: "Products",
        Connection = "CosmosDBConnection")]
    public async Task<object?> RunAsync(
        [CosmosDBTrigger(
                databaseName: "GAB2025",
                containerName: "Products",
                Connection = "CosmosDBConnection",
                LeaseContainerName = "leases",
                CreateLeaseContainerIfNotExists = true)] IReadOnlyList<dynamic> input,
        FunctionContext context)
    {
        try
        {
            // List of documents to be returned to output binding
            var toBeUpdated = new List<(JsonDocument doc, string hash, List<string> toEmbed)>();

            if (input?.Count > 0)
            {
                _logger.LogInformation("Documents modified: {count}", input.Count);
                for (int i = 0; i < input.Count; i++)
                {
                    var document = input[i];

                    // Parse document into a json object
                    JsonDocument jsonDocument = JsonDocument.Parse(document.ToString());

                    // Check hash value to see if document is new or modified
                    if (IsDocumentNewOrModified(jsonDocument, out var newHash))
                    {
                        var propertiesToEmbed = new List<string>();
                        foreach (var property in _propertiesToEmbed)
                        {
                            if (jsonDocument.RootElement.TryGetProperty(property, out JsonElement propertyElement))
                            {
                                propertiesToEmbed.Add(propertyElement.GetString() ?? string.Empty);
                            }
                        }
                        toBeUpdated.Add((jsonDocument, newHash, propertiesToEmbed));
                    }
                }
            }

            // Process documents that have been modified
            if (toBeUpdated.Count > 0)
            {
                _logger.LogInformation("Updating embeddings for: {count}", toBeUpdated.Count);

                // Generate embeddings on the specified document property or document
                var embeddings = await GetEmbeddingsAsync(toBeUpdated.SelectMany(tbu => tbu.toEmbed));

                StringBuilder output = new StringBuilder().AppendLine("[");
                for (int i = 0; i < toBeUpdated.Count; i++)
                {
                    var (jsonDocument, hash, toEmbed) = toBeUpdated[i];

                    // Create a new JSON object with the updated properties
                    using var stream = new MemoryStream();
                    using (var writer = new Utf8JsonWriter(stream))
                    {
                        writer.WriteStartObject();

                        foreach (JsonProperty property in jsonDocument.RootElement.EnumerateObject())
                        {
                            if (property.Name != _hashProperty && property.Name != _vectorProperty)
                            {
                                property.WriteTo(writer);
                            }
                        }

                        writer.WriteString(_hashProperty, hash);
                        writer.WriteStartArray(_vectorProperty);
                        foreach (var value in embeddings[i])
                        {
                            writer.WriteNumberValue(value);
                        }
                        writer.WriteEndArray();

                        writer.WriteEndObject();
                    }

                    stream.Position = 0;
                    var updatedJsonDocument = JsonDocument.Parse(stream);
                    output.Append(updatedJsonDocument.RootElement.GetRawText());
                    output.AppendLine(",");
                }
                output.Length -= 1 + Environment.NewLine.Length;
                output.AppendLine().AppendLine("]");

                return output.ToString();
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing documents " + ex.Message);
        }

        return null;
    }

    private bool IsDocumentNewOrModified(JsonDocument jsonDocument, out string newHash)
    {
        if (jsonDocument.RootElement.TryGetProperty(_hashProperty, out JsonElement existingProperty))
        {
            // Generate a hash of the document/property
            newHash = ComputeJsonHash(jsonDocument);

            // Document has changed, process it
            if (newHash != existingProperty.GetString())
                return true;

            // Document has not changed, skip processing
            return false;
        }
        else
        {
            // No hash property, document is new
            newHash = ComputeJsonHash(jsonDocument);
            return true;
        }
    }

    private async Task<List<float[]>> GetEmbeddingsAsync(IEnumerable<string> inputs)
    {
        // The dimensions parameter specifies the number of dimensions for the embedding vectors.
        // An embedding is a numerical representation of the input text in a high-dimensional space.
        // Each input string will be converted into a vector of floats with the specified number of dimensions.
        var options = new EmbeddingGenerationOptions
        {
            Dimensions = _dimensions
        };

        var response = await _embeddingClient.GenerateEmbeddingsAsync(inputs, options);
        var results = new List<float[]>(response.Value.Count);
        foreach (var e in response.Value)
        {
            results.Add(e.ToFloats().ToArray());
        }
        return results;
    }

    private string ComputeJsonHash(JsonDocument jsonDocument)
    {

        // Cleanse the document of system, vector and hash properties
        jsonDocument = RemoveProperties(jsonDocument);

        // Compute a hash on entire document generating embeddings on entire document
        // Re-serialize the JSON to canonical form (sorted keys, no extra whitespace)

        // Generate a hash on the property to be embedded
        var combinedProperties = string.Join("", _propertiesToEmbed.Select(p =>
        {
            jsonDocument.RootElement.TryGetProperty(p, out JsonElement propertyElement);
            return propertyElement.GetString() ?? string.Empty;
        }));

        // Compute SHA256 hash
        byte[] hashBytes = SHA256.HashData(Encoding.UTF8.GetBytes(combinedProperties));
        return BitConverter.ToString(hashBytes).Replace("-", "").ToLowerInvariant();
    }

    private JsonDocument RemoveProperties(JsonDocument jsonDocument)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();

            foreach (JsonProperty property in jsonDocument.RootElement.EnumerateObject())
            {
                if (property.Name != _vectorProperty &&
                    property.Name != _hashProperty &&
                    property.Name != "_rid" &&
                    property.Name != "_self" &&
                    property.Name != "_etag" &&
                    property.Name != "_attachments" &&
                    property.Name != "_lsn" &&
                    property.Name != "_ts")
                {
                    property.WriteTo(writer);
                }
            }

            writer.WriteEndObject();
        }

        stream.Position = 0;
        return JsonDocument.Parse(stream);
    }
}
